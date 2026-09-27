<template>
  <view class="page" :class="cwRootClass">
    <scroll-view scroll-y class="msg-scroll" :scroll-into-view="anchor" :scroll-with-animation="true">
      <view class="msg-list">
        <view
          v-for="m in messages" :key="m.id" :id="'msg-' + m.id"
          :class="['msg-row', m.sender_id === myId ? 'mine' : '']"
        >
          <view class="bubble anim-right">{{ m.content }}</view>
        </view>
        <view v-if="messages.length === 0" class="empty-tip">
          发送消息开始聊天吧～私信内容同样受敏感词与举报保护
        </view>
      </view>
    </scroll-view>
    <view class="input-bar safe-bottom">
      <view class="bar-inner">
        <input v-model="text" class="msg-input" placeholder="说点什么…" confirm-type="send" @confirm="send" />
        <button class="send-btn" @click="send" :disabled="sending">发送</button>
      </view>
    </view>
  </view>
</template>
<script setup>
import { ref, nextTick } from 'vue'
import { onLoad, onUnload } from '@dcloudio/uni-app'
import { api } from '../../utils/api'
import { realtime } from '../../utils/ws'
const conversationId = ref(0)
const myId = ref(0)
const messages = ref([])
const text = ref('')
const sending = ref(false)
const anchor = ref('')
let timer = null
let offWs = []
// WS 在线时完全不轮询；断开时用这个较慢的间隔兜底，保证功能不退化。
// 改造前是固定 2.5 秒轮询：N 个在线用户就是 N/2.5 QPS 的恒定背景压力，
// 且消息延迟最高 2.5 秒。现在延迟接近 0，请求量下降一到两个数量级。
const FALLBACK_POLL = 15000
const scrollToBottom = () => {
  nextTick(() => {
    const last = messages.value[messages.value.length - 1]
    if (last) anchor.value = 'msg-' + last.id
  })
}
const markRead = () => {
  api.readConversation(conversationId.value).catch(() => {})
  uni.$emit('badge:refresh')
}
const loadMessages = async () => {
  try {
    const data = await api.getMessages(conversationId.value, { page: 1, page_size: 50 })
    const newItems = data.items
    const lastOld = messages.value[messages.value.length - 1]
    if (!lastOld || newItems.length !== messages.value.length ||
        newItems[newItems.length - 1].id !== lastOld.id) {
      messages.value = newItems
      scrollToBottom()
      // 正在聊天页：对方新消息立即标已读，红点实时消除
      const last = newItems[newItems.length - 1]
      if (last && last.sender_id !== myId.value) markRead()
    }
  } catch (e) {}
}
const send = async () => {
  const content = text.value.trim()
  if (!content || sending.value) return
  sending.value = true
  try {
    await api.sendMessage(conversationId.value, content)
    text.value = ''
    await loadMessages()
  } catch (e) {} finally {
    sending.value = false
  }
}
// 根据 WS 连接状态决定是否启用兜底轮询
const adjustPolling = () => {
  if (timer) { clearInterval(timer); timer = null }
  if (!realtime.isConnected()) timer = setInterval(loadMessages, FALLBACK_POLL)
}
// 只处理「当前会话」的推送；其他会话的消息交给收件箱页与角标
const onWsFrame = (frame) => {
  if (!frame || Number(frame.conversation_id) !== Number(conversationId.value)) return
  loadMessages()
}
const onWsState = () => adjustPolling()
onLoad((options) => {
  conversationId.value = parseInt(options.id)
  const userInfo = uni.getStorageSync('userInfo')
  myId.value = userInfo ? JSON.parse(userInfo).id : 0
  if (options.peerName) {
    try { uni.setNavigationBarTitle({ title: decodeURIComponent(options.peerName) }) }
    catch (e) { uni.setNavigationBarTitle({ title: options.peerName }) }
  }
  loadMessages()
  markRead()
  realtime.connect()
  offWs = [
    realtime.on('message', onWsFrame),
    realtime.on('open', onWsState),
    realtime.on('close', onWsState),
  ]
  adjustPolling()
})
onUnload(() => {
  if (timer) { clearInterval(timer); timer = null }
  offWs.forEach((off) => { try { off() } catch (e) {} })
  offWs = []
  uni.$emit('badge:refresh')
})
</script>
<style scoped>
.page { display: flex; flex-direction: column; height: 100vh; background: var(--bg); }
.msg-scroll { flex: 1; overflow: hidden; }
.msg-list { padding: 28rpx; }
.msg-row { display: flex; margin-bottom: 24rpx; }
.msg-row.mine { justify-content: flex-end; }
.bubble {
  max-width: 72%; padding: 20rpx 28rpx; border-radius: 24rpx;
  background: var(--surface); color: var(--ink); font-size: 29rpx; line-height: 1.55;
  word-break: break-word; box-shadow: var(--shadow-sm);
  border: 1rpx solid var(--line);
}
.msg-row.mine .bubble {
  background: var(--brand); color: #fff; border-color: var(--brand);
}
.empty-tip { text-align: center; color: var(--ink-3); font-size: 24rpx; padding: 80rpx 60rpx; line-height: 1.8; }
.input-bar {
  position: fixed; bottom: 0; left: 0; right: 0; background: var(--surface);
  border-top: 1rpx solid var(--line); padding: 14rpx 24rpx; z-index: 99;
}
.bar-inner { display: flex; align-items: center; gap: 16rpx; }
.msg-input {
  flex: 1; height: 76rpx; background: #f2f3f6; border-radius: 999rpx;
  padding: 0 30rpx; font-size: 28rpx;
}
.send-btn {
  background: var(--brand); color: #fff; font-size: 27rpx; height: 76rpx;
  line-height: 76rpx; padding: 0 44rpx; border-radius: 999rpx; border: none; margin: 0;
}
.send-btn[disabled] { opacity: 0.5; }
/* #ifdef H5 */
@media (min-width: 768px) {
  .input-bar { max-width: 720px; margin: 0 auto; }
}
@media (min-width: 1100px) {
  .input-bar { max-width: 780px; }
}
/* #endif */
</style>
