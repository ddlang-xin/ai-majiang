import 'dart:io';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'package:permission_handler/permission_handler.dart';
import 'pages/realtime_battle_page.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();
  
  // 加载配置
  final settings = await AppSettings.load();
  
  // 请求相机权限
  final cameraStatus = await Permission.camera.request();
  if (cameraStatus.isDenied) {
    runApp(MaiJiangApp(settings: settings));
    return;
  }
  
  // 获取可用摄像头列表
  final cameras = await availableCameras();
  if (cameras.isEmpty) {
    runApp(MaiJiangApp(settings: settings));
    return;
  }
  
  runApp(MaiJiangApp(cameras: cameras, settings: settings));
}

// ==================== 配置管理 ====================
class AppSettings {
  int zhaNiaoCount; // 扎鸟数 (0, 2, 4, 6)
  bool isQidui; // 是否起手对子胡
  bool isHaiDiLao; // 是否海底捞月
  bool is Tianhu; // 是否天胡
  bool is Dihu; // 是否地胡
  String apiBaseUrl; // API地址
  
  AppSettings({
    this.zhaNiaoCount = 2,
    this.isQidui = false,
    this.isHaiDiLao = true,
    this.isTianhu = true,
    this.isDihu = true,
    this.apiBaseUrl = 'http://localhost:8080',
  });
  
  factory AppSettings.load() {
    // 默认配置，实际可以从SharedPreferences加载
    return AppSettings();
  }
  
  Map<String, dynamic> toJson() => {
    'zhaNiaoCount': zhaNiaoCount,
    'isQidui': isQidui,
    'isHaiDiLao': isHaiDiLao,
    'isTianhu': isTianhu,
    'isDihu': isDihu,
    'apiBaseUrl': apiBaseUrl,
  };
}

class MaiJiangApp extends StatelessWidget {
  final List<CameraDescription>? cameras;
  final AppSettings settings;
  
  const MaiJiangApp({Key? key, this.cameras, required this.settings}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'AI麻将助手',
      theme: ThemeData(
        primarySwatch: Colors.green,
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: Colors.green[700]!),
      ),
      home: MainNavigation(cameras: cameras, settings: settings),
    );
  }
}

// ==================== 主导航 ====================
class MainNavigation extends StatefulWidget {
  final List<CameraDescription>? cameras;
  final AppSettings settings;
  
  const MainNavigation({Key? key, this.cameras, required this.settings}) : super(key: key);

  @override
  State<MainNavigation> createState() => _MainNavigationState();
}

class _MainNavigationState extends State<MainNavigation> {
  int _currentIndex = 0;
  late AppSettings _settings;
  
  @override
  void initState() {
    super.initState();
    _settings = widget.settings;
  }
  
  void _updateSettings(AppSettings newSettings) {
    setState(() {
      _settings = newSettings;
    });
  }

  @override
  Widget build(BuildContext context) {
    final pages = [
      HomePage(cameras: widget.cameras, settings: _settings),
      if (widget.cameras != null && widget.cameras!.isNotEmpty)
        RealtimeBattlePage(cameras: widget.cameras!),
      AnalysisHistoryPage(),
      SettingsPage(settings: _settings, onSettingsChanged: _updateSettings),
    ];
    
    return Scaffold(
      body: pages[_currentIndex],
      bottomNavigationBar: NavigationBar(
        selectedIndex: _currentIndex,
        onDestinationSelected: (index) {
          setState(() {
            _currentIndex = index;
          });
        },
        destinations: [
          const NavigationDestination(
            icon: Icon(Icons.camera_alt_outlined),
            selectedIcon: Icon(Icons.camera_alt),
            label: '拍照',
          ),
          if (widget.cameras != null && widget.cameras!.isNotEmpty)
            const NavigationDestination(
              icon: Icon(Icons.videocam_outlined),
              selectedIcon: Icon(Icons.videocam),
              label: '实时',
            ),
          const NavigationDestination(
            icon: Icon(Icons.history_outlined),
            selectedIcon: Icon(Icons.history),
            label: '历史',
          ),
          const NavigationDestination(
            icon: Icon(Icons.settings_outlined),
            selectedIcon: Icon(Icons.settings),
            label: '设置',
          ),
        ],
      ),
    );
  }
}

// ==================== 首页（拍照页） ====================
class HomePage extends StatefulWidget {
  final List<CameraDescription>? cameras;
  final AppSettings settings;
  
  const HomePage({Key? key, this.cameras, required this.settings}) : super(key: key);

  @override
  State<HomePage> createState() => _HomePageState();
}

class _HomePageState extends State<HomePage> {
  CameraController? _controller;
  bool _isInitializing = true;
  String? _errorMessage;
  XFile? _capturedImage;
  AnalysisResult? _analysisResult;
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    _initCamera();
  }

  Future<void> _initCamera() async {
    if (widget.cameras == null || widget.cameras!.isEmpty) {
      setState(() {
        _isInitializing = false;
        _errorMessage = '未检测到摄像头';
      });
      return;
    }
    
    try {
      final camera = widget.cameras!.firstWhere(
        (cam) => cam.lensDirection == CameraLensDirection.back,
        orElse: () => widget.cameras!.first,
      );
      
      _controller = CameraController(
        camera,
        ResolutionPreset.high,
        enableAudio: false,
      );
      
      await _controller!.initialize();
      
      if (mounted) {
        setState(() {
          _isInitializing = false;
        });
      }
    } catch (e) {
      setState(() {
        _isInitializing = false;
        _errorMessage = '相机初始化失败: $e';
      });
    }
  }

  @override
  void dispose() {
    _controller?.dispose();
    super.dispose();
  }

  Future<void> _captureImage() async {
    if (_controller == null || !_controller!.value.isInitialized) {
      return;
    }
    
    try {
      final image = await _controller!.takePicture();
      setState(() {
        _capturedImage = image;
        _analysisResult = null;
        _isLoading = true;
      });
      
      await _sendToAI(image);
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('拍照失败: $e')),
      );
    }
  }

  Future<void> _sendToAI(XFile image) async {
    try {
      final bytes = await image.readAsBytes();
      final base64Image = base64Encode(bytes);
      
      final response = await http.post(
        Uri.parse('${widget.settings.apiBaseUrl}/api/analyze'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'image': base64Image,
          'settings': widget.settings.toJson(),
        }),
      ).timeout(const Duration(seconds: 30));
      
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          _analysisResult = AnalysisResult.fromJson(data);
          _isLoading = false;
        });
      } else {
        setState(() {
          _analysisResult = AnalysisResult(
            recommendation: '分析失败: ${response.statusCode}',
            tiles: [],
            discardTile: null,
            reason: '',
          );
          _isLoading = false;
        });
      }
    } catch (e) {
      // 模拟数据演示
      setState(() {
        _analysisResult = _generateMockResult();
        _isLoading = false;
      });
    }
  }

  AnalysisResult _generateMockResult() {
    // 模拟识别到的麻将牌数据
    final recognizedTiles = [
      RecognizedTile(tile: '🀇', name: '一万', confidence: 0.98, suit: '万'),
      RecognizedTile(tile: '🀇', name: '一万', confidence: 0.95, suit: '万'),
      RecognizedTile(tile: '🀈', name: '二万', confidence: 0.97, suit: '万'),
      RecognizedTile(tile: '🀉', name: '三万', confidence: 0.96, suit: '万'),
      RecognizedTile(tile: '🀊', name: '四万', confidence: 0.94, suit: '万'),
      RecognizedTile(tile: '🀋', name: '五万', confidence: 0.99, suit: '万'),
      RecognizedTile(tile: '🀌', name: '六万', confidence: 0.97, suit: '万'),
      RecognizedTile(tile: '🀍', name: '七万', confidence: 0.93, suit: '万'),
      RecognizedTile(tile: '🀎', name: '八万', confidence: 0.91, suit: '万'),
      RecognizedTile(tile: '🀏', name: '九万', confidence: 0.96, suit: '万'),
      RecognizedTile(tile: '🀀', name: '东风', confidence: 0.92, suit: '风'),
      RecognizedTile(tile: '🀁', name: '南风', confidence: 0.88, suit: '风'),
      RecognizedTile(tile: '🀂', name: '西风', confidence: 0.95, suit: '风'),
      RecognizedTile(tile: '🀃', name: '北风', confidence: 0.90, suit: '风'),
      RecognizedTile(tile: '🀄', name: '红中', confidence: 0.99, suit: '箭'),
    ];
    
    return AnalysisResult(
      recommendation: '听牌！建议打出 🀇 一万',
      tiles: ['🀇', '🀈', '🀉', '🀊', '🀋', '🀌', '🀍', '🀎', '🀏', '🀀', '🀁', '🀂', '🀃', '🀄'],
      discardTile: '🀇',
      reason: '当前手牌已形成【二三四五六七八】顺子+【中中中】刻子+【發】雀头，听【一万】，打出一万可听牌',
      handType: '断幺九',
      tingCount: 1,
      isHu: false,
      recognizedTiles: recognizedTiles,
    );
  }

  void _retake() {
    setState(() {
      _capturedImage = null;
      _analysisResult = null;
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI麻将助手'),
        backgroundColor: Colors.green[700],
        foregroundColor: Colors.white,
        actions: [
          IconButton(
            icon: const Icon(Icons.flash_off),
            onPressed: () {},
          ),
          if (widget.cameras != null && widget.cameras!.isNotEmpty)
            IconButton(
              icon: const Icon(Icons.videocam),
              tooltip: '实时对战',
              onPressed: () {
                Navigator.of(context).push(
                  MaterialPageRoute(
                    builder: (context) => RealtimeBattlePage(cameras: widget.cameras!),
                  ),
                );
              },
            ),
        ],
      ),
      body: _buildBody(),
    );
  }

  Widget _buildBody() {
    if (_isInitializing) {
      return const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            CircularProgressIndicator(color: Colors.green),
            SizedBox(height: 16),
            Text('正在初始化相机...'),
          ],
        ),
      );
    }
    
    if (_errorMessage != null) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              const Icon(Icons.error_outline, size: 64, color: Colors.red),
              const SizedBox(height: 16),
              Text(_errorMessage!, textAlign: TextAlign.center),
              const SizedBox(height: 24),
              ElevatedButton(
                onPressed: () {
                  setState(() {
                    _isInitializing = true;
                    _errorMessage = null;
                  });
                  _initCamera();
                },
                child: const Text('重试'),
              ),
            ],
          ),
        ),
      );
    }
    
    if (_capturedImage != null) {
      return _buildResultView();
    }
    
    return _buildCameraPreview();
  }

  Widget _buildCameraPreview() {
    return Column(
      children: [
        // 相机预览区域
        Expanded(
          flex: 3,
          child: Container(
            margin: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              border: Border.all(color: Colors.green[700]!, width: 2),
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(14),
              child: CameraPreview(_controller!),
            ),
          ),
        ),
        
        // 说明文字
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20),
          child: Text(
            '将麻将牌放入画面中央，点击拍摄按钮',
            style: TextStyle(color: Colors.grey[600], fontSize: 14),
            textAlign: TextAlign.center,
          ),
        ),
        
        // 拍摄按钮
        Padding(
          padding: const EdgeInsets.all(30),
          child: GestureDetector(
            onTap: _captureImage,
            child: Container(
              width: 80,
              height: 80,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: Colors.green[700]!, width: 4),
              ),
              child: Container(
                margin: const EdgeInsets.all(4),
                decoration: const BoxDecoration(
                  shape: BoxShape.circle,
                  color: Colors.green,
                ),
                child: const Icon(Icons.camera_alt, color: Colors.white, size: 36),
              ),
            ),
          ),
        ),
        
        const SizedBox(height: 20),
      ],
    );
  }

  Widget _buildResultView() {
    return SingleChildScrollView(
      child: Column(
        children: [
          // 拍摄的照片
          Container(
            margin: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(16),
              boxShadow: [
                BoxShadow(
                  color: Colors.black.withOpacity(0.1),
                  blurRadius: 10,
                  offset: const Offset(0, 4),
                ),
              ],
            ),
            child: ClipRRect(
              borderRadius: BorderRadius.circular(16),
              child: Image.file(File(_capturedImage!.path), fit: BoxFit.cover),
            ),
          ),
          
          // AI分析结果
          if (_isLoading)
            const Padding(
              padding: EdgeInsets.all(20),
              child: Column(
                children: [
                  CircularProgressIndicator(color: Colors.green),
                  SizedBox(height: 16),
                  Text('AI正在分析中...'),
                ],
              ),
            )
          else if (_analysisResult != null)
            _buildAnalysisCard(_analysisResult!),
          
          // 重新拍摄按钮
          Padding(
            padding: const EdgeInsets.all(16),
            child: ElevatedButton.icon(
              onPressed: _retake,
              icon: const Icon(Icons.camera_alt),
              label: const Text('重新拍摄'),
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green[700],
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 12),
              ),
            ),
          ),
        ],
      ),
    );
  }

  // Glassmorphism 风格识别结果卡片
  Widget _buildRecognitionCard(List<RecognizedTile> recognizedTiles) {
    return Container(
      margin: const EdgeInsets.fromLTRB(16, 16, 16, 0),
      decoration: BoxDecoration(
        // Glassmorphism 效果
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [
            Colors.white.withOpacity(0.25),
            Colors.white.withOpacity(0.15),
          ],
        ),
        borderRadius: BorderRadius.circular(20),
        border: Border.all(
          color: Colors.white.withOpacity(0.3),
          width: 1.5,
        ),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withOpacity(0.1),
            blurRadius: 20,
            offset: const Offset(0, 10),
          ),
        ],
      ),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(20),
        child: BackdropFilter(
          filter: ColorFilter.mode(
            Colors.white.withOpacity(0.2),
            BlendMode.srcOver,
          ),
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // 标题
                Row(
                  children: [
                    Container(
                      padding: const EdgeInsets.all(8),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.3),
                        borderRadius: BorderRadius.circular(10),
                      ),
                      child: const Icon(
                        Icons.document_scanner_outlined,
                        color: Colors.white,
                        size: 20,
                      ),
                    ),
                    const SizedBox(width: 10),
                    const Text(
                      '🔍 识别结果',
                      style: TextStyle(
                        fontSize: 16,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                      ),
                    ),
                    const Spacer(),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                      decoration: BoxDecoration(
                        color: Colors.white.withOpacity(0.25),
                        borderRadius: BorderRadius.circular(12),
                      ),
                      child: Text(
                        '${recognizedTiles.length} 张',
                        style: const TextStyle(
                          color: Colors.white,
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ),
                  ],
                ),
                
                const SizedBox(height: 16),
                
                // 识别到的麻将牌列表
                Wrap(
                  spacing: 8,
                  runSpacing: 8,
                  children: recognizedTiles.map((tile) => _buildTileChip(tile)).toList(),
                ),
                
                const SizedBox(height: 16),
                
                // 置信度统计
                _buildConfidenceStats(recognizedTiles),
              ],
            ),
          ),
        ),
      ),
    );
  }
  
  // 单个麻将牌识别结果Chip
  Widget _buildTileChip(RecognizedTile tile) {
    final confidencePercent = (tile.confidence * 100).toStringAsFixed(0);
    final confidenceColor = _getConfidenceColor(tile.confidence);
    
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.2),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: Colors.white.withOpacity(0.3),
          width: 1,
        ),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Text(
            tile.tile,
            style: const TextStyle(fontSize: 22),
          ),
          const SizedBox(width: 6),
          Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                tile.name,
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 11,
                  fontWeight: FontWeight.w500,
                ),
              ),
              Row(
                children: [
                  Container(
                    width: 40,
                    height: 4,
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.3),
                      borderRadius: BorderRadius.circular(2),
                    ),
                    child: FractionallySizedBox(
                      alignment: Alignment.centerLeft,
                      widthFactor: tile.confidence,
                      child: Container(
                        decoration: BoxDecoration(
                          color: confidenceColor,
                          borderRadius: BorderRadius.circular(2),
                        ),
                      ),
                    ),
                  ),
                  const SizedBox(width: 4),
                  Text(
                    '$confidencePercent%',
                    style: TextStyle(
                      color: confidenceColor,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
    );
  }
  
  // 根据置信度获取颜色
  Color _getConfidenceColor(double confidence) {
    if (confidence >= 0.95) return Colors.green[300]!;
    if (confidence >= 0.90) return Colors.lightGreen[200]!;
    if (confidence >= 0.80) return Colors.yellow[200]!;
    return Colors.orange[200]!;
  }
  
  // 置信度统计
  Widget _buildConfidenceStats(List<RecognizedTile> tiles) {
    final high = tiles.where((t) => t.confidence >= 0.95).length;
    final medium = tiles.where((t) => t.confidence >= 0.90 && t.confidence < 0.95).length;
    final low = tiles.where((t) => t.confidence < 0.90).length;
    
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: Colors.white.withOpacity(0.15),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceAround,
        children: [
          _buildStatItem('高置信', high, Colors.green[300]!),
          Container(width: 1, height: 30, color: Colors.white.withOpacity(0.3)),
          _buildStatItem('中置信', medium, Colors.yellow[200]!),
          Container(width: 1, height: 30, color: Colors.white.withOpacity(0.3)),
          _buildStatItem('低置信', low, Colors.orange[200]!),
        ],
      ),
    );
  }
  
  Widget _buildStatItem(String label, int count, Color color) {
    return Column(
      children: [
        Text(
          '$count',
          style: TextStyle(
            color: color,
            fontSize: 20,
            fontWeight: FontWeight.bold,
          ),
        ),
        Text(
          label,
          style: TextStyle(
            color: Colors.white.withOpacity(0.8),
            fontSize: 11,
          ),
        ),
      ],
    );
  }

  Widget _buildAnalysisCard(AnalysisResult result) {
    return Column(
      children: [
        // 识别结果 - Glassmorphism 风格
        if (result.recognizedTiles.isNotEmpty)
          _buildRecognitionCard(result.recognizedTiles),
        
        // AI分析结果
        Container(
          margin: const EdgeInsets.all(16),
          decoration: BoxDecoration(
            color: Colors.green[50],
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: Colors.green[300]!, width: 1),
          ),
          child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // 标题栏
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: Colors.green[700],
              borderRadius: const BorderRadius.vertical(top: Radius.circular(15)),
            ),
            child: Row(
              children: [
                const Icon(Icons.smart_toy, color: Colors.white),
                const SizedBox(width: 8),
                const Text(
                  'AI 智能分析',
                  style: TextStyle(
                    fontSize: 18,
                    fontWeight: FontWeight.bold,
                    color: Colors.white,
                  ),
                ),
                const Spacer(),
                if (result.isHu)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.red,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: const Text('🔔 胡了!', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                  )
                else if (result.tingCount > 0)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 4),
                    decoration: BoxDecoration(
                      color: Colors.orange,
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Text('🎯 ${result.tingCount}张听牌', style: const TextStyle(color: Colors.white)),
                  ),
              ],
            ),
          ),
          
          // 手牌展示
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('🀄 识别手牌', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 8),
                Wrap(
                  spacing: 4,
                  runSpacing: 4,
                  children: result.tiles.map((tile) => Text(tile, style: const TextStyle(fontSize: 24))).toList(),
                ),
              ],
            ),
          ),
          
          const Divider(height: 1),
          
          // 推荐出牌
          if (result.discardTile != null)
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  const Text('📤 推荐打出: ', style: TextStyle(fontSize: 16)),
                  Text(result.discardTile!, style: const TextStyle(fontSize: 32)),
                ],
              ),
            ),
          
          const Divider(height: 1),
          
          // 分析原因
          Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text('📝 分析理由', style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16)),
                const SizedBox(height: 8),
                Text(result.reason, style: const TextStyle(fontSize: 14, height: 1.5)),
              ],
            ),
          ),
          
          // 番型提示
          if (result.handType.isNotEmpty)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: Wrap(
                spacing: 8,
                children: result.handType.split(',').map((type) => 
                  Chip(
                    label: Text(type, style: const TextStyle(fontSize: 12)),
                    backgroundColor: Colors.green[100],
                  )
                ).toList(),
              ),
            ),
        ],
      ),
    );
  }
}

// ==================== 识别结果模型 ====================
class RecognizedTile {
  final String tile;        // 麻将牌emoji
  final String name;       // 牌名
  final double confidence; // 置信度 0-1
  final String suit;       // 花色 (万/条/筒/风/箭)
  
  RecognizedTile({
    required this.tile,
    required this.name,
    required this.confidence,
    required this.suit,
  });
  
  factory RecognizedTile.fromJson(Map<String, dynamic> json) {
    return RecognizedTile(
      tile: json['tile'] ?? '',
      name: json['name'] ?? '',
      confidence: (json['confidence'] ?? 0.0).toDouble(),
      suit: json['suit'] ?? '',
    );
  }
  
  Map<String, dynamic> toJson() => {
    'tile': tile,
    'name': name,
    'confidence': confidence,
    'suit': suit,
  };
}

// ==================== 分析结果模型 ====================
class AnalysisResult {
  final String recommendation;
  final List<String> tiles;
  final String? discardTile;
  final String reason;
  final String handType;
  final int tingCount;
  final bool isHu;
  final List<RecognizedTile> recognizedTiles; // 识别到的牌及置信度
  
  AnalysisResult({
    required this.recommendation,
    required this.tiles,
    this.discardTile,
    required this.reason,
    this.handType = '',
    this.tingCount = 0,
    this.isHu = false,
    this.recognizedTiles = const [],
  });
  
  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    return AnalysisResult(
      recommendation: json['recommendation'] ?? '',
      tiles: List<String>.from(json['tiles'] ?? []),
      discardTile: json['discardTile'],
      reason: json['reason'] ?? '',
      handType: json['handType'] ?? '',
      tingCount: json['tingCount'] ?? 0,
      isHu: json['isHu'] ?? false,
      recognizedTiles: (json['recognizedTiles'] as List<dynamic>?)
          ?.map((e) => RecognizedTile.fromJson(e))
          .toList() ?? [],
    );
  }
}

// ==================== 历史记录页 ====================
class AnalysisHistoryPage extends StatelessWidget {
  // TODO: 后续可以接入本地存储显示历史记录
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('历史记录'),
        backgroundColor: Colors.green[700],
        foregroundColor: Colors.white,
      ),
      body: const Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.history, size: 64, color: Colors.grey),
            SizedBox(height: 16),
            Text('暂无历史记录', style: TextStyle(color: Colors.grey)),
            SizedBox(height: 8),
            Text('拍照分析后会显示在这里', style: TextStyle(color: Colors.grey, fontSize: 12)),
          ],
        ),
      ),
    );
  }
}

// ==================== 设置页 ====================
class SettingsPage extends StatefulWidget {
  final AppSettings settings;
  final Function(AppSettings) onSettingsChanged;
  
  const SettingsPage({Key? key, required this.settings, required this.onSettingsChanged}) : super(key: key);

  @override
  State<SettingsPage> createState() => _SettingsPageState();
}

class _SettingsPageState extends State<SettingsPage> {
  late AppSettings _settings;
  
  @override
  void initState() {
    super.initState();
    _settings = widget.settings;
  }
  
  void _saveSettings() {
    widget.onSettingsChanged(_settings);
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(content: Text('设置已保存')),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('游戏设置'),
        backgroundColor: Colors.green[700],
        foregroundColor: Colors.white,
      ),
      body: ListView(
        children: [
          // 扎鸟数设置
          _buildSectionHeader('🎯 扎鸟设置'),
          _buildZhaNiaoSelector(),
          
          const Divider(),
          
          // 番型设置
          _buildSectionHeader('⚡ 番型设置'),
          SwitchListTile(
            title: const Text('起手对子胡'),
            subtitle: const Text('起手4对子可直接胡牌'),
            value: _settings.isQidui,
            onChanged: (value) => setState(() => _settings.isQidui = value),
          ),
          SwitchListTile(
            title: const Text('海底捞月'),
            subtitle: const Text('海底牌胡牌'),
            value: _settings.isHaiDiLao,
            onChanged: (value) => setState(() => _settings.isHaiDiLao = value),
          ),
          SwitchListTile(
            title: const Text('天胡'),
            subtitle: const Text('庄家起手胡牌'),
            value: _settings.isTianhu,
            onChanged: (value) => setState(() => _settings.isTianhu = value),
          ),
          SwitchListTile(
            title: const Text('地胡'),
            subtitle: const Text('闲家摸第一张牌前胡牌'),
            value: _settings.isDihu,
            onChanged: (value) => setState(() => _settings.isDihu = value),
          ),
          
          const Divider(),
          
          // API设置
          _buildSectionHeader('🔌 API设置'),
          ListTile(
            title: const Text('后端API地址'),
            subtitle: Text(_settings.apiBaseUrl),
            trailing: const Icon(Icons.chevron_right),
            onTap: () => _showApiUrlDialog(),
          ),
          
          const Divider(),
          
          // 关于
          _buildSectionHeader('ℹ️ 关于'),
          const ListTile(
            title: Text('AI麻将助手'),
            subtitle: Text('版本 1.0.0'),
            leading: Icon(Icons.info_outline),
          ),
          
          // 保存按钮
          Padding(
            padding: const EdgeInsets.all(16),
            child: ElevatedButton(
              onPressed: _saveSettings,
              style: ElevatedButton.styleFrom(
                backgroundColor: Colors.green[700],
                foregroundColor: Colors.white,
                padding: const EdgeInsets.symmetric(vertical: 16),
              ),
              child: const Text('保存设置', style: TextStyle(fontSize: 16)),
            ),
          ),
        ],
      ),
    );
  }
  
  Widget _buildSectionHeader(String title) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
      child: Text(
        title,
        style: TextStyle(
          fontSize: 14,
          fontWeight: FontWeight.bold,
          color: Colors.green[700],
        ),
      ),
    );
  }
  
  Widget _buildZhaNiaoSelector() {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text('扎鸟数量', style: TextStyle(fontSize: 16)),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceEvenly,
            children: [0, 2, 4, 6].map((count) {
              final isSelected = _settings.zhaNiaoCount == count;
              return GestureDetector(
                onTap: () => setState(() => _settings.zhaNiaoCount = count),
                child: Container(
                  width: 60,
                  height: 60,
                  decoration: BoxDecoration(
                    color: isSelected ? Colors.green[700] : Colors.grey[200],
                    borderRadius: BorderRadius.circular(12),
                    border: isSelected ? null : Border.all(color: Colors.grey[400]!),
                  ),
                  child: Center(
                    child: Text(
                      '$count',
                      style: TextStyle(
                        fontSize: 20,
                        fontWeight: FontWeight.bold,
                        color: isSelected ? Colors.white : Colors.grey[700],
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
          const SizedBox(height: 8),
          Text(
            '扎中1鸟=1分，2鸟=2分，以此类推',
            style: TextStyle(fontSize: 12, color: Colors.grey[600]),
          ),
        ],
      ),
    );
  }
  
  void _showApiUrlDialog() {
    final controller = TextEditingController(text: _settings.apiBaseUrl);
    showDialog(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('修改API地址'),
        content: TextField(
          controller: controller,
          decoration: const InputDecoration(
            hintText: '例如: http://192.168.1.100:8080',
            border: OutlineInputBorder(),
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('取消'),
          ),
          ElevatedButton(
            onPressed: () {
              setState(() {
                _settings.apiBaseUrl = controller.text;
              });
              Navigator.pop(context);
            },
            child: const Text('确定'),
          ),
        ],
      ),
    );
  }
}
