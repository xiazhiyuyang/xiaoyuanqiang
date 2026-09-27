// 实时通道（WebSocket）封装
// WS是优化不是依赖：连不上时页面退回轮询继续工作。
// 用法：import { realtime } from '../../utils/ws'
//   realtime.on('message', handler)  // 注册监听（返回取消函数）
//   realtime.connect()                // 幂等，重复调用不会开第二条连接
//   realtime.isConnected()            // false时调用方应启用轮询兜底
import { WS_URL } from './api'

const HEARTBEAT_INTERVAL = 30000   // 客户端心跳，需小于服务端 90s 接收超时
const RECONNECT_DELAYS = [1000, 2000, 4000, 8000, 15000, 30000]

class Realtime {
  constructor() {
    this.task = null
    this.connected = false
    this.manualClose = false
    this.retry = 0
    this.reconnectTimer = null
    this.heartbeatTimer = null
    this.listeners = new Map()   // type -> Set<fn>
    this.lastWelcome = null
  }

  on(type, fn) {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set())
    this.listeners.get(type).add(fn)
    return () => this.off(type, fn)
  }

  off(type, fn) {
    const set = this.listeners.get(type)
    if (set) set.delete(fn)
  }

  emit(type, payload) {
    const set = this.listeners.get(type)
    if (!set) return
    set.forEach((fn) => {
      try { fn(payload) } catch (e) { console.error('[ws] handler error', type, e) }
    })
  }

  isConnected() {
    return this.connected
  }

  connect() {
    const token = uni.getStorageSync('token')
    if (!token) return          // 未登录不建连
    if (this.task || this.connected) return   // 幂等
    this.manualClose = false

    let task
    try {
      task = uni.connectSocket({
        url: `${WS_URL}?token=${encodeURIComponent(token)}`,
        complete: () => {},
      })
    } catch (e) {
      this._scheduleReconnect()
      return
    }
    // uni.connectSocket 在部分平台返回 undefined（需用全局 onSocketMessage），
    // 这里统一走 SocketTask 实例；拿不到实例就放弃 WS，让调用方轮询兜底。
    if (!task || typeof task.onOpen !== 'function') {
      this._scheduleReconnect()
      return
    }
    this.task = task

    task.onOpen(() => {
      this.connected = true
      this.retry = 0
      this._startHeartbeat()
      this.emit('open', {})
    })

    task.onMessage((res) => {
      let frame
      try { frame = JSON.parse(res.data) } catch (e) { return }
      if (!frame || !frame.type) return
      if (frame.type === 'welcome') this.lastWelcome = frame
      if (frame.type === 'ping') return   // 服务端心跳，无需回应
      this.emit(frame.type, frame)
      this.emit('*', frame)
    })

    task.onError(() => {
      // 交给 onClose 统一处理，避免重复重连
    })

    task.onClose((e) => {
      this.connected = false
      this._stopHeartbeat()
      this.task = null
      this.emit('close', e || {})
      // 4401 = 服务端判定 token 失效：清登录态，不再重连
      if (e && e.code === 4401) {
        uni.removeStorageSync('token')
        uni.removeStorageSync('userInfo')
        this.emit('unauthorized', {})
        return
      }
      if (!this.manualClose) this._scheduleReconnect()
    })
  }

  _startHeartbeat() {
    this._stopHeartbeat()
    this.heartbeatTimer = setInterval(() => {
      if (!this.connected || !this.task) return
      try { this.task.send({ data: JSON.stringify({ type: 'ping' }) }) } catch (e) { /* 忽略 */ }
    }, HEARTBEAT_INTERVAL)
  }

  _stopHeartbeat() {
    if (this.heartbeatTimer) { clearInterval(this.heartbeatTimer); this.heartbeatTimer = null }
  }

  _scheduleReconnect() {
    if (this.manualClose) return
    if (this.reconnectTimer) return
    const delay = RECONNECT_DELAYS[Math.min(this.retry, RECONNECT_DELAYS.length - 1)]
    this.retry += 1
    // 超过重试上限后停止自动重连，避免在弱网下无意义耗电；
    // 页面 onShow 会再调一次 connect() 重新拉起。
    if (this.retry > RECONNECT_DELAYS.length) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this.connect()
    }, delay)
  }

  close() {
    this.manualClose = true
    this._stopHeartbeat()
    if (this.reconnectTimer) { clearTimeout(this.reconnectTimer); this.reconnectTimer = null }
    if (this.task) {
      try { this.task.close({ code: 1000 }) } catch (e) { /* 忽略 */ }
      this.task = null
    }
    this.connected = false
  }
}

export const realtime = new Realtime()
export default realtime
