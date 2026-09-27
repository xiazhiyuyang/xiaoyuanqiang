// 统一安全跳转：
// - 站内 /pages/ 路径直接跳
// - http(s) 外链弹确认框，防钓鱼/越权诱导
// - 其他协议（javascript:、vbefile: 等）一律拦截
export const openSafeLink = (url) => {
  if (!url) return
  const u = String(url).trim()
  // 站内页面
  if (u.startsWith('/pages/')) {
    uni.navigateTo({ url: u, fail: () => uni.switchTab({ url: u, fail: () => {} }) })
    return
  }
  if (/^https?:\/\//i.test(u)) {
    let host = u
    try { host = new URL(u).host } catch (e) { host = u }
    uni.showModal({
      title: '即将离开校园墙',
      content: `是否打开外部链接？\n${host}`,
      confirmText: '打开',
      cancelText: '取消',
      success: (r) => {
        if (!r.confirm) return
        // #ifdef H5
        window.open(u, '_blank', 'noopener,noreferrer')
        // #endif
        // #ifndef H5
        uni.setClipboardData({
          data: u,
          success: () => uni.showToast({ title: '链接已复制，请到浏览器打开', icon: 'none' }),
        })
        // #endif
      },
    })
    return
  }
  // 可疑协议直接拦截
  uni.showToast({ title: '该链接不受支持，已拦截', icon: 'none' })
}
