<template>
  <view class="page" :class="cwRootClass">
    <view class="doc-card cw-card anim-up">
      <text class="doc-title">校园墙隐私政策与用户协议</text>
      <text class="doc-update">更新日期：2026 年 8 月 29 日　生效日期：2026 年 8 月 29 日</text>
      <text class="doc-lead">
        欢迎使用校园墙（以下简称「本平台」）。我们深知个人信息对您的重要性，会按照法律法规要求采取相应安全保护措施。
        本协议说明我们如何收集、使用、存储、共享和保护您的信息，以及您享有的权利。请您在注册、登录或使用本平台前仔细阅读并充分理解，
        勾选「已阅读并同意」即表示您已知晓并接受本协议全部内容。
      </text>

      <text class="h2">一、我们收集的信息</text>
      <text class="h3">1. 账号注册信息</text>
      <text class="p">· 注册时需要提供：用户名、昵称、登录密码（密码经加密哈希存储，工作人员无法查看明文）。</text>
      <text class="p">· 选填信息：学号、手机号，仅用于身份核验、账号找回，不强制提供。</text>
      <text class="p">· 若使用微信一键登录，我们会在您授权后获取微信 OpenID 用于创建/关联账号，不会获取您的微信好友、聊天记录等信息。</text>
      <text class="h3">2. 个人资料信息</text>
      <text class="p">· 您可自主完善头像、个人简介、性别、年级、学院、专业、校区、生日等资料；上述信息的公开范围可在「我的-设置-隐私设置」中设置为公开、仅会员可见或仅自己可见。</text>
      <text class="h3">3. 您发布与互动的内容</text>
      <text class="p">· 您发布的帖子（含文字、图片、视频）、评论、点赞、收藏、关注关系、私信内容，以及您提交的举报和反馈。</text>
      <text class="p">· 匿名发布时，平台会对其他用户隐藏您的身份，但平台基于安全管理仍保留真实发布记录。</text>
      <text class="h3">4. 设备与日志信息</text>
      <text class="p">· 为保障账号与社区安全，我们会记录登录时间、IP 地址、操作日志、被封禁/审核记录，用于违规排查、风控与审计。</text>
      <text class="h3">5. 本地存储信息</text>
      <text class="p">· 我们会在您的设备本地保存登录凭证、主题外观等设置；退出登录或清除缓存后即被清理。</text>

      <text class="h2">二、我们如何使用信息</text>
      <text class="p">1. 提供发帖、评论、点赞、收藏、关注、私信、消息通知、等级成长等社区功能；</text>
      <text class="p">2. 对内容进行敏感词过滤、人工/随机审核与举报处理，维护社区秩序；</text>
      <text class="p">3. 进行账号安全验证、密码找回、异常登录防护；</text>
      <text class="p">4. 向您展示公告、活动横幅等运营信息（不会用于向第三方出售个人数据）；</text>
      <text class="p">5. 生成去标识化的统计数据，用于改进产品体验。</text>

      <text class="h2">三、信息的共享、公开与披露</text>
      <text class="p">1. 除以下情形外，我们不会向任何第三方共享您的个人信息：获得您的明确同意；法律法规要求或行政、司法机关依法定程序提出要求；为维护平台及用户合法权益（如处理诈骗、人身安全紧急情况）。</text>
      <text class="p">2. 您公开发布的内容（含匿名内容）会在社区内对其他用户可见，请避免在帖子中泄露自己或他人的手机号、住址、证件号等敏感信息。</text>
      <text class="p">3. 私信内容仅对话双方可见，工作人员仅在收到举报并核实涉嫌违法违规时按流程查阅。</text>

      <text class="h2">四、信息的存储与保护</text>
      <text class="p">1. 您的信息存储在平台服务器中，传输与存储采取加密、访问权限控制、操作审计等保护措施；</text>
      <text class="p">2. 我们仅在实现目的所必需的最短期限内保留您的信息；账号注销后将按法律要求删除或匿名化处理；</text>
      <text class="p">3. 如发生信息安全事件，我们将依法及时启动应急预案并告知您。</text>

      <text class="h2">五、您的权利</text>
      <text class="p">1. 查阅与更正：您可在「编辑资料」中查看、修改个人资料；</text>
      <text class="p">2. 隐私设置：您可自主设置各资料项的可见范围；</text>
      <text class="p">3. 删除：您可删除自己发布的内容；删除后不再公开展示；</text>
      <text class="p">4. 退出与注销：您可随时退出登录；如需注销账号，可联系管理员处理，注销后账号资料将被清除；</text>
      <text class="p">5. 若您对个人信息处理有疑问，可通过「设置-联系我们」或学校社区管理渠道与我们联系。</text>

      <text class="h2">六、社区行为规范（用户协议）</text>
      <text class="p">1. 您应保证注册信息真实，不得冒用他人身份，不得将账号出借、转让；</text>
      <text class="p">2. 禁止发布违法违规、色情暴力、人身攻击、造谣传谣、代写代考、兼职刷单、引流交易等内容；平台有权对违规内容进行屏蔽、删除，对账号采取警告、封禁等措施；</text>
      <text class="p">3. 二手交易、失物招领等信息请发布到对应分类，自行核实交易风险，平台不参与线下交易，不承担交易纠纷责任；</text>
      <text class="p">4. 请尊重他人隐私与肖像权，未经允许不得曝光他人姓名、联系方式、照片等信息；</text>
      <text class="p">5. 您发布的原创内容著作权归您所有，同时授权平台在社区范围内进行展示与传播。</text>

      <text class="h2">七、未成年人保护</text>
      <text class="p">本平台面向在校学生，未成年人应在监护人指导下阅读本协议并使用平台；我们不会主动收集未成年人敏感信息，若监护人发现相关问题可联系我们处理。</text>

      <text class="h2">八、协议的更新</text>
      <text class="p">本协议可能根据法律法规变化或功能调整进行更新，更新后将在本页面公布并标注更新日期；重大变更会以公告等方式提示，您继续使用即视为接受更新后的协议。</text>

      <text class="h2">九、其他</text>
      <text class="p">1. 本协议的解释、效力及争议解决适用中华人民共和国法律；</text>
      <text class="p">2. 本协议任何条款被认定无效，不影响其他条款的效力；</text>
      <text class="p">3. 如您不同意本协议任何内容，应停止注册和使用本平台。</text>

      <view class="agree-btn btn hover-press" @click="confirm">我已阅读并同意</view>
    </view>
  </view>
</template>
<script setup>
const confirm = () => {
  const pages = getCurrentPages()
  if (pages.length > 1) uni.navigateBack()
  else uni.switchTab({ url: '/pages/index/index' })
}
</script>
<style scoped>
.page { min-height: 100vh; background: var(--bg); padding: 24rpx 24rpx 60rpx; }
.doc-card { padding: 36rpx 30rpx; }
.doc-title { display: block; font-size: 40rpx; font-weight: 800; color: var(--ink); text-align: center; line-height: 1.4; }
.doc-update { display: block; text-align: center; color: var(--ink-3); font-size: 22rpx; margin-top: 14rpx; }
.doc-lead { display: block; margin-top: 26rpx; color: var(--ink-2); font-size: 25rpx; line-height: 1.75; text-align: justify; }
.h2 { display: block; margin-top: 34rpx; font-size: 30rpx; font-weight: 800; color: var(--ink); }
.h3 { display: block; margin-top: 18rpx; font-size: 26rpx; font-weight: 700; color: var(--brand, #8b7cf6); }
.p { display: block; margin-top: 10rpx; color: var(--ink-2); font-size: 25rpx; line-height: 1.75; text-align: justify; }
.agree-btn { margin-top: 40rpx; }
</style>
