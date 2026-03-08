/// 摄像头相关枚举定义

/// 分辨率预设
enum CameraResolutionPreset {
  /// 低分辨率 (320x240)
  low,
  
  /// 中分辨率 (640x480)
  medium,
  
  /// 高分辨率 (1024x768)
  high,
  
  /// 超高分辨率 (1280x720)
  veryHigh,
  
  /// 最高分辨率 (1920x1080)
  highest,
  
  /// 4K分辨率 (3840x2160)
  ultraHigh,
}

/// 摄像头位置
enum CameraPosition {
  /// 后置摄像头
  back,
  
  /// 前置摄像头
  front,
}

/// 摄像头状态
enum CameraStatus {
  /// 未初始化
  uninitialized,
  
  /// 初始化中
  initializing,
  
  /// 已初始化/工作中
  ready,
  
  /// 错误状态
  error,
  
  /// 已释放
  disposed,
}
