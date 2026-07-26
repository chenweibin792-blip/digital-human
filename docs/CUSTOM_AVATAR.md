# 自定义 Avatar

请只使用你拥有肖像权、版权和用途授权的素材。默认 Avatar 未附带商业肖像许可。

LiveTalking 已保留 Avatar 注册机制。新增或替换实现前，先阅读 `registry.py`、
`avatars/` 和现有 Wav2Lip 准备流程，不要在路由中硬编码另一套推理架构。

Wav2Lip Avatar 目录至少需要：

```text
data\avatars\<avatar_id>\
  coords.pkl
  full_imgs\
  face_imgs\
```

准备完成后先运行：

```powershell
.\scripts\check_models.ps1 -AvatarId <avatar_id>
.\start.ps1 -AvatarId <avatar_id>
```

素材、坐标、缓存和权重均不得提交到 Git。更换 Avatar 后应重新验证画面比例、
嘴型区域、音画同步、内存、十条消息稳定性和停止后恢复。

未来切换 MuseTalk 时，应通过现有 `avatar` registry 注册新实现，并通过
`--model` 选择；MuseTalk 模型、依赖及许可需要单独审核和测试。

