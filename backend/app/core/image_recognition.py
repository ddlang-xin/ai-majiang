"""
图像识别API模块
预留YOLO模型接口，用于识别麻将牌
"""

from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from enum import Enum
import base64
import numpy as np
from pathlib import Path


class DetectionModel(str, Enum):
    """检测模型"""
    YOLO_V8 = "yolov8"
    YOLO_V5 = "yolov5"
    CUSTOM = "custom"


class ImageFormat(str, Enum):
    """图像格式"""
    BASE64 = "base64"
    URL = "url"
    FILE = "file"


class RecognitionRequest(BaseModel):
    """图像识别请求"""
    image: str = Field(..., description="图像数据（base64/URL/文件路径）")
    format: ImageFormat = Field(default=ImageFormat.BASE64, description="图像格式")
    model: DetectionModel = Field(default=DetectionModel.YOLO_V8, description="使用的模型")
    confidence: float = Field(default=0.5, description="置信度阈值")
    detect_hand: bool = Field(default=True, description="是否识别手牌")
    detect_discarded: bool = Field(default=True, description="是否识别打出的牌")
    detect_drawn: bool = Field(default=True, description="是否识别摸到的牌")


class TilePosition(BaseModel):
    """牌位置"""
    x: float = Field(..., description="x坐标")
    y: float = Field(description="y坐标")
    width: float = Field(..., description="宽度")
    height: float = Field(description="高度")


class TileDetection(BaseModel):
    """牌检测结果"""
    tile: str = Field(..., description="牌面（如'1W'）")
    position: TilePosition = Field(..., description="位置")
    confidence: float = Field(..., description="置信度")


class RecognitionResponse(BaseModel):
    """图像识别响应"""
    success: bool
    hand_tiles: List[TileDetection] = Field(default_factory=list, description="手牌")
    discarded_tiles: List[TileDetection] = Field(default_factory=list, description="打过的牌")
    drawn_tile: Optional[TileDetection] = Field(default=None, description="摸到的牌")
    all_tiles: List[TileDetection] = Field(default_factory=list, description="所有检测到的牌")
    processing_time: float = Field(..., description="处理时间(秒)")
    model_used: str = Field(..., description="使用的模型")
    message: Optional[str] = None


class YOLORecognizer:
    """YOLO麻将牌识别器"""
    
    def __init__(self, model_path: str = None):
        """
        初始化识别器
        :param model_path: 模型文件路径
        """
        self.model = None
        self.model_path = model_path
        self.is_loaded = False
        
        # 牌面映射（根据训练集类别）
        self.tile_classes = self._init_tile_classes()
    
    def _init_tile_classes(self) -> Dict[int, str]:
        """初始化牌类映射"""
        # 标准麻将34种牌
        classes = {}
        
        # 万子 0-8
        for i in range(1, 10):
            classes[i - 1] = f"{i}W"
        
        # 筒子 9-17
        for i in range(1, 10):
            classes[i + 8] = f"{i}T"
        
        # 条子 18-26
        for i in range(1, 10):
            classes[i + 17] = f"{i}S"
        
        # 字牌 27-33
        classes[27] = "D"   # 东
        classes[28] = "N"   # 南
        classes[29] = "X"   # 西
        classes[30] = "B"   # 北
        classes[31] = "Z"   # 中
        classes[32] = "F"   # 发
        classes[33] = "Bai" # 白
        
        return classes
    
    def load_model(self, model_path: str = None) -> bool:
        """加载模型"""
        try:
            # 尝试导入ultralytics（YOLO）
            from ultralytics import YOLO
            
            path = model_path or self.model_path or "best.pt"
            if Path(path).exists():
                self.model = YOLO(path)
                self.is_loaded = True
                return True
            else:
                # 模型文件不存在，使用模拟模式
                self.is_loaded = False
                return False
        except ImportError:
            # ultralytics未安装，使用模拟模式
            self.is_loaded = False
            return False
        except Exception as e:
            print(f"加载模型失败: {e}")
            self.is_loaded = False
            False
    
    def recognize(self, image_data: str, format: ImageFormat = ImageFormat.BASE64) -> RecognitionResponse:
        """
        识别图像中的麻将牌
        :param image_data: 图像数据
        :param format: 图像格式
        :return: 识别结果
        """
        import time
        start_time = time.time()
        
        # 加载模型（如需要）
        if not self.is_loaded:
            self.load_model()
        
        # 加载图像
        try:
            image = self._load_image(image_data, format)
        except Exception as e:
            return RecognitionResponse(
                success=False,
                processing_time=time.time() - start_time,
                model_used="mock",
                message=f"图像加载失败: {str(e)}"
            )
        
        # 执行识别
        if self.is_loaded and self.model:
            detections = self._detect_with_model(image)
        else:
            # 模拟模式：返回示例数据
            detections = self._mock_detect()
        
        # 分类检测结果
        result = self._classify_detections(detections)
        
        result.success = True
        result.processing_time = time.time() - start_time
        result.model_used = "yolov8" if self.is_loaded else "mock"
        
        return result
    
    def _load_image(self, image_data: str, format: ImageFormat):
        """加载图像"""
        from PIL import Image
        import io
        
        if format == ImageFormat.BASE64:
            # Base64解码
            img_data = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(img_data))
        elif format == ImageFormat.URL:
            # 从URL下载
            import requests
            from PIL import Image
            import io
            response = requests.get(image_data)
            image = Image.open(io.BytesIO(response.content))
        elif format == ImageFormat.FILE:
            # 文件路径
            image = Image.open(image_data)
        else:
            raise ValueError(f"不支持的图像格式: {format}")
        
        return image
    
    def _detect_with_model(self, image) -> List[Dict]:
        """使用模型检测"""
        results = self.model(image, conf=0.5)
        
        detections = []
        for result in results:
            boxes = result.boxes
            for box in boxes:
                # 获取类别和置信度
                cls_id = int(box.cls[0])
                conf = float(box.conf[0])
                
                # 获取位置
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                
                detections.append({
                    "class_id": cls_id,
                    "class_name": self.tile_classes.get(cls_id, f"unknown_{cls_id}"),
                    "confidence": conf,
                    "x": x1,
                    "y": y1,
                    "width": x2 - x1,
                    "height": y2 - y1
                })
        
        return detections
    
    def _mock_detect(self) -> List[Dict]:
        """模拟检测（无模型时使用）"""
        # 返回示例数据
        return [
            {"class_id": 0, "class_name": "1W", "confidence": 0.95, "x": 100, "y": 400, "width": 50, "height": 70},
            {"class_id": 1, "class_name": "2W", "confidence": 0.93, "x": 155, "y": 400, "width": 50, "height": 70},
            {"class_id": 2, "class_name": "3W", "confidence": 0.91, "x": 210, "y": 400, "width": 50, "height": 70},
            {"class_id": 9, "class_name": "1T", "confidence": 0.89, "x": 265, "y": 400, "width": 50, "height": 70},
        ]
    
    def _classify_detections(self, detections: List[Dict]) -> RecognitionResponse:
        """分类检测结果"""
        all_tiles = []
        
        for det in detections:
            tile_detection = TileDetection(
                tile=det["class_name"],
                position=TilePosition(
                    x=det["x"],
                    y=det["y"],
                    width=det["width"],
                    height=det["height"]
                ),
                confidence=det["confidence"]
            )
            all_tiles.append(tile_detection)
        
        # 按位置排序（手牌在下方，打过的牌在上方）
        all_tiles.sort(key=lambda t: t.position.y)
        
        # 简单分类：y > 300 为手牌，y < 300 为其他
        hand_tiles = [t for t in all_tiles if t.position.y > 300]
        other_tiles = [t for t in all_tiles if t.position.y <= 300]
        
        return RecognitionResponse(
            success=False,  # 临时，会在最后设置
            all_tiles=all_tiles,
            hand_tiles=hand_tiles,
            discarded_tiles=other_tiles,
            processing_time=0,
            model_used="unknown"
        )


# 全局识别器实例
recognizer = YOLORecognizer()


def recognize_tiles(
    image_data: str,
    format: ImageFormat = ImageFormat.BASE64,
    model: DetectionModel = DetectionModel.YOLO_V8
) -> RecognitionResponse:
    """
    识别麻将牌（快捷函数）
    :param image_data: 图像数据
    :param format: 图像格式
    :param model: 使用的模型
    :return: 识别结果
    """
    return recognizer.recognize(image_data, format)


# 异步版本
async def recognize_tiles_async(
    image_data: str,
    format: ImageFormat = ImageFormat.BASE64,
    model: DetectionModel = DetectionModel.YOLO_V8
) -> RecognitionResponse:
    """异步识别麻将牌"""
    import asyncio
    
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, 
        recognize_tiles, 
        image_data, 
        format, 
        model
    )


# 测试
if __name__ == "__main__":
    # 测试识别器
    rec = YOLORecognizer()
    rec.load_model()
    
    # 模拟识别
    result = rec.recognize("", ImageFormat.BASE64)
    print(f"识别结果: {result}")
