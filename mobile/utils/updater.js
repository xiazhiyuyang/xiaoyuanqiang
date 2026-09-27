import { api, resolveServerUrl } from './api'
let checking = false
let downloading = false
const VERSION_FALLBACK = {
  version: '1.0.0',
  versionCode: 100,
}
export const compareVersion = (current = '', latest = '') => {
  const currentParts = String(current).split('.').map((item) => Number.parseInt(item, 10) || 0)
  const latestParts = String(latest).split('.').map((item) => Number.parseInt(item, 10) || 0)
  const length = Math.max(currentParts.length, latestParts.length)
  for (let i = 0; i < length; i += 1) {
    const diff = (latestParts[i] || 0) - (currentParts[i] || 0)
    if (diff !== 0) return diff > 0 ? 1 : -1
  }
  return 0
}
export const getRuntimeInfo = () => new Promise((resolve) => {
  let info = { ...VERSION_FALLBACK }
  // #ifdef APP-PLUS
  plus.runtime.getProperty(plus.runtime.appid, (widgetInfo) => {
    resolve({
      version: widgetInfo?.version || VERSION_FALLBACK.version,
      versionCode: Number(widgetInfo?.versionCode || VERSION_FALLBACK.versionCode),
    })
  })
  return
  // #endif
  // #ifndef APP-PLUS
  resolve(info)
  // #endif
})
const getPlatform = () => {
  const systemInfo = uni.getSystemInfoSync()
  return systemInfo.platform === 'ios' ? 'ios' : 'android'
}
// 通用下载：返回本地文件路径，onProgress(0-99) 回调进度
const createDownload = (url, savePath, onProgress) => new Promise((resolve, reject) => {
  // #ifdef APP-PLUS
  const task = plus.downloader.createDownload(
    url,
    { filename: savePath, retry: 1, timeout: 180 },
    (download, status) => {
      if (status === 200) resolve(download.filename)
      else reject(new Error(`下载失败，HTTP ${status}`))
    },
  )
  task.addEventListener('statechanged', (download) => {
    if (download.state === 3 && download.totalSize) {
      const percent = Math.min(99, Math.round((download.downloadedSize / download.totalSize) * 100))
      onProgress?.(percent)
    }
  })
  task.start()
  return
  // #endif
  reject(new Error('当前平台不支持下载更新包'))
})
// 把 5+ 本地相对路径转为系统绝对路径（整包安装需要真实文件路径）
const toAbsoluteLocalPath = (filePath) => {
  // #ifdef APP-PLUS
  try {
    if (plus.io && typeof plus.io.convertLocalFileSystemURL === 'function') {
      const abs = plus.io.convertLocalFileSystemURL(filePath)
      if (abs) return abs
    }
  } catch (e) { /* 回退原始路径 */ }
  // #endif
  return filePath
}
// 冷更新：安装整包（Android 调起系统安装器；iOS 直接跳 App Store）
const installPackage = (filePath, storeUrl) => new Promise((resolve, reject) => {
  // #ifdef APP-PLUS
  const platform = getPlatform()
  if (platform === 'ios') {
    // iOS 不允许侧载安装包，整包更新只能跳转 App Store / TestFlight
    if (storeUrl) {
      plus.runtime.openURL(storeUrl)
      resolve()
      return
    }
    reject(new Error('未配置 App Store 下载地址'))
    return
  }
  // Android：调起系统 PackageInstaller，用户确认后覆盖安装（数据保留）
  const target = toAbsoluteLocalPath(filePath)
  plus.runtime.install(
    target,
    { force: false },
    () => resolve(),
    (err) => {
      // 部分机型绝对路径失败时，回退用 5+ 相对路径再试一次
      if (target !== filePath) {
        plus.runtime.install(filePath, { force: false }, () => resolve(), (e2) => reject(e2 || err))
      } else {
        reject(err)
      }
    },
  )
  return
  // #endif
  reject(new Error('当前平台不支持整包安装'))
})
// 冷更新（整包 APK / IPA）流程
const runColdUpdate = async (packageUrl, platform) => {
  // #ifdef APP-PLUS
  if (platform === 'ios') {
    // iOS 没有安装包过程，直接跳商店
    plus.runtime.openURL(packageUrl)
    return
  }
  downloading = true
  uni.showLoading({ title: '正在下载安装包 0%', mask: true })
  const filePath = await createDownload(packageUrl, '_doc/campus-wall/update/apk/', (percent) => {
    uni.showLoading({ title: `下载安装包 ${percent}%`, mask: true })
  })
  uni.hideLoading()
  uni.showToast({ title: '下载完成，正在调起安装', icon: 'none' })
  await installPackage(filePath, packageUrl)
  // #endif
}
// 弹出更新确认；required 时不允许取消，取消后继续弹
const confirmUpdate = (release) => new Promise((resolve) => {
  const show = () => {
    uni.showModal({
      title: `发现新版本 ${release.latest_version}${release.required ? '（必须更新）' : ''}`,
      content: release.changelog || '优化体验，修复已知问题。',
      confirmText: '立即更新',
      cancelText: '以后再说',
      showCancel: !release.required,
    }).then((modal) => {
      if (modal.confirm) resolve(true)
      else if (release.required) setTimeout(show, 300) // 强制更新：绕不开，继续提示
      else resolve(false)
    }).catch(() => {
      if (release.required) setTimeout(show, 300)
      else resolve(false)
    })
  }
  show()
})
export const checkAppUpdate = async ({ silent = true } = {}) => {
  if (checking || downloading) return null
  // #ifndef APP-PLUS
  if (!silent) uni.showToast({ title: '更新仅 App 端可用', icon: 'none' })
  return null
  // #endif
  // #ifdef APP-PLUS
  checking = true
  try {
    const runtime = await getRuntimeInfo()
    const platform = getPlatform()
    const release = await api.getAppVersion({
      platform,
      version: runtime.version,
      version_code: runtime.versionCode,
    })
    const hasUpdate = release?.has_update || compareVersion(runtime.version, release?.latest_version) > 0
    if (!hasUpdate) {
      if (!silent) uni.showToast({ title: '已是最新版本', icon: 'none' })
      return release
    }
    // 仅支持整包 APK 冷更新：下载完整安装包并调起系统安装器覆盖安装
    const packageUrl = resolveServerUrl(release.apk_url)
    // 未配置整包下载地址，属于后台未配置完整
    if (!packageUrl) {
      if (!silent) uni.showToast({ title: '更新包地址未配置', icon: 'none' })
      return release
    }
    const confirmed = await confirmUpdate(release)
    if (!confirmed) return release
    try {
      // 整包冷更新：下载完整安装包并调起系统安装器（用户数据保留）
      await runColdUpdate(packageUrl, platform)
    } catch (error) {
      console.error('App update failed:', error)
      // 下载/安装失败：允许重试；强制更新时不可退出
      const retry = await new Promise((resolve) => {
        uni.showModal({
          title: '更新失败',
          content: `${error?.message || '下载或安装失败'}，是否重试？`,
          confirmText: '重试',
          cancelText: release.required ? '退出' : '以后再说',
          showCancel: true,
        }).then((m) => resolve(!!m.confirm)).catch(() => resolve(false))
      })
      if (retry) {
        downloading = false
        return checkAppUpdate({ silent: false })
      }
    }
    return release
  } catch (error) {
    console.error('Check update failed:', error)
    if (!silent) {
      uni.showModal({
        title: '检查更新失败',
        content: error?.message || '请稍后重试，或到官网下载最新安装包。',
        showCancel: false,
      })
    }
    return null
  } finally {
    checking = false
    downloading = false
    uni.hideLoading()
  }
  // #endif
}
