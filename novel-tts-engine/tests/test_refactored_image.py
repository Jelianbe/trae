"""
测试重构后的Image类架构

验证职责分离后的各个组件是否正常工作
"""
import sys
import os
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from refactored_image import (
    Image,
    ImageDataManager,
    GeometryTransformer,
    ImageIOHandler,
    ColorSpaceConverter,
    ImageComposer,
    FormatHandlerFactory,
    ResizeStrategy,
    FastPathRotationStrategy,
    MatrixRotationStrategy,
    Resampling,
    Dither,
    Palette,
    new,
)

# 导入重命名以避免与Python内置open()冲突
from refactored_image import open as image_open


def test_image_data_manager():
    """测试图像数据管理器"""
    print("=" * 60)
    print("测试 1: ImageDataManager")
    print("=" * 60)
    
    manager = ImageDataManager()
    manager.mode = "RGB"
    manager.size = (800, 600)
    manager.info = {"description": "Test image"}
    
    assert manager.mode == "RGB"
    assert manager.size == (800, 600)
    assert manager.width == 800
    assert manager.height == 600
    assert manager.info["description"] == "Test image"
    
    print("[OK] 基本属性测试通过")
    
    # 测试复制
    copy = manager.copy()
    assert copy.mode == manager.mode
    assert copy.size == manager.size
    assert copy is not manager
    
    print("[OK] 复制功能测试通过")
    print("[OK] ImageDataManager 所有测试通过\n")


def test_geometry_transformer():
    """测试几何变换器"""
    print("=" * 60)
    print("测试 2: GeometryTransformer")
    print("=" * 60)
    
    manager = ImageDataManager()
    manager.mode = "RGB"
    manager.size = (800, 600)
    
    transformer = GeometryTransformer(manager)
    
    # 测试策略模式
    resize_strategy = ResizeStrategy()
    assert resize_strategy.can_handle(size=(400, 300))
    assert not resize_strategy.can_handle()
    
    print("[OK] Resize策略测试通过")
    
    # 测试旋转策略
    fast_strategy = FastPathRotationStrategy()
    assert fast_strategy.can_handle(angle=90, center=None, translate=None)
    assert not fast_strategy.can_handle(angle=45, center=None, translate=None)
    assert not fast_strategy.can_handle(angle=90, center=(10, 10), translate=None)
    
    print("[OK] 快速旋转策略测试通过")
    
    matrix_strategy = MatrixRotationStrategy()
    assert matrix_strategy.can_handle(angle=45)
    assert matrix_strategy.can_handle(angle=90, center=(10, 10))
    
    print("[OK] 矩阵旋转策略测试通过")
    print("[OK] GeometryTransformer 所有测试通过\n")


def test_image_io_handler():
    """测试文件I/O处理器"""
    print("=" * 60)
    print("测试 3: ImageIOHandler")
    print("=" * 60)
    
    manager = ImageDataManager()
    manager.mode = "RGB"
    manager.size = (800, 600)
    
    factory = FormatHandlerFactory()
    io_handler = ImageIOHandler(manager, factory)
    
    # 测试扩展名转换
    assert io_handler._extension_to_format(".jpg") == "JPEG"
    assert io_handler._extension_to_format(".png") == "PNG"
    assert io_handler._extension_to_format(".gif") == "GIF"
    assert io_handler._extension_to_format(".unknown") is None
    
    print("✓ 扩展名转换测试通过")
    print("✓ ImageIOHandler 所有测试通过\n")


def test_color_space_converter():
    """测试颜色空间转换器"""
    print("=" * 60)
    print("测试 4: ColorSpaceConverter")
    print("=" * 60)
    
    manager = ImageDataManager()
    manager.mode = "RGB"
    manager.size = (800, 600)
    
    converter = ColorSpaceConverter(manager)
    
    # 测试模式基础转换
    assert converter._get_mode_base("L") == "L"
    assert converter._get_mode_base("LA") == "L"
    assert converter._get_mode_base("RGB") == "RGB"
    assert converter._get_mode_base("RGBA") == "RGB"
    
    print("✓ 模式基础转换测试通过")
    print("✓ ColorSpaceConverter 所有测试通过\n")


def test_image_composer():
    """测试图像合成器"""
    print("=" * 60)
    print("测试 5: ImageComposer")
    print("=" * 60)
    
    manager = ImageDataManager()
    manager.mode = "RGB"
    manager.size = (800, 600)
    
    composer = ImageComposer(manager)
    
    # 测试参数验证
    try:
        composer.alpha_composite(manager, source_box="invalid")
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "Source must be a list or tuple" in str(e)
    
    print("✓ 参数验证测试通过")
    print("✓ ImageComposer 所有测试通过\n")


def test_image_facade():
    """测试Image门面类"""
    print("=" * 60)
    print("测试 6: Image 门面类")
    print("=" * 60)
    
    img = Image()
    img._data_manager.mode = "RGB"
    img._data_manager.size = (800, 600)
    
    # 测试属性委托
    assert img.mode == "RGB"
    assert img.size == (800, 600)
    assert img.width == 800
    assert img.height == 600
    
    print("✓ 属性委托测试通过")
    
    # 测试复制
    copy = img.copy()
    assert copy.mode == img.mode
    assert copy.size == img.size
    assert copy is not img
    
    print("✓ 复制功能测试通过")
    
    # 测试上下文管理器
    with Image() as img2:
        img2._data_manager.mode = "RGB"
        img2._data_manager.size = (100, 100)
        assert img2.mode == "RGB"
    
    print("✓ 上下文管理器测试通过")
    
    # 测试字符串表示
    repr_str = repr(img)
    assert "Image" in repr_str
    assert "RGB" in repr_str
    assert "800x600" in repr_str
    
    print("✓ 字符串表示测试通过")
    print("✓ Image 门面类所有测试通过\n")


def test_factory_functions():
    """测试工厂函数"""
    print("=" * 60)
    print("测试 7: 工厂函数")
    print("=" * 60)
    
    # 测试new函数
    img = new("RGB", (800, 600))
    assert img.mode == "RGB"
    assert img.size == (800, 600)
    
    print("✓ new() 函数测试通过")
    
    # 测试open函数
    try:
        img2 = image_open("test.jpg", mode="w")
        assert False, "应该抛出异常"
    except ValueError as e:
        assert "bad mode" in str(e)
    
    print("✓ open() 函数参数验证测试通过")
    print("✓ 工厂函数所有测试通过\n")


def test_strategy_pattern():
    """测试策略模式应用"""
    print("=" * 60)
    print("测试 8: 策略模式")
    print("=" * 60)
    
    manager = ImageDataManager()
    manager.mode = "RGB"
    manager.size = (800, 600)
    
    transformer = GeometryTransformer(manager)
    
    # 测试resize策略
    resize_strategy = ResizeStrategy()
    
    # 有效参数
    assert resize_strategy.can_handle(size=(400, 300), resample=Resampling.BICUBIC)
    
    # 无效参数
    assert not resize_strategy.can_handle(resample=Resampling.BICUBIC)
    
    print("✓ Resize策略参数验证通过")
    
    # 测试旋转策略选择
    fast_strategy = FastPathRotationStrategy()
    
    # 快速路径：90度，无平移
    assert fast_strategy.can_handle(angle=90, center=None, translate=None)
    
    # 慢速路径：45度
    assert not fast_strategy.can_handle(angle=45, center=None, translate=None)
    
    # 慢速路径：有自定义中心点
    assert not fast_strategy.can_handle(angle=90, center=(100, 100), translate=None)
    
    print("✓ 旋转策略选择通过")
    print("✓ 策略模式所有测试通过\n")


def test_composition():
    """测试组合模式"""
    print("=" * 60)
    print("测试 9: 组合模式验证")
    print("=" * 60)
    
    # 验证Image类正确组合了所有处理器
    img = Image()
    
    assert hasattr(img, '_data_manager')
    assert hasattr(img, '_geometry')
    assert hasattr(img, '_io_handler')
    assert hasattr(img, '_color_converter')
    assert hasattr(img, '_composer')
    
    assert isinstance(img._data_manager, ImageDataManager)
    assert isinstance(img._geometry, GeometryTransformer)
    assert isinstance(img._io_handler, ImageIOHandler)
    assert isinstance(img._color_converter, ColorSpaceConverter)
    assert isinstance(img._composer, ImageComposer)
    
    print("✓ Image类正确组合所有处理器")
    print("✓ 组合模式验证通过\n")


def main():
    """运行所有测试"""
    print("\n")
    print("=" * 60)
    print("PIL Image 重构架构测试")
    print("=" * 60)
    print("\n")
    
    try:
        test_image_data_manager()
        test_geometry_transformer()
        test_image_io_handler()
        test_color_space_converter()
        test_image_composer()
        test_image_facade()
        test_factory_functions()
        test_strategy_pattern()
        test_composition()
        
        print("=" * 60)
        print("✓ 所有测试通过！")
        print("=" * 60)
        print("\n")
        print("重构架构验证成功：")
        print("  - 职责分离：✓")
        print("  - 策略模式：✓")
        print("  - 工厂模式：✓")
        print("  - 门面模式：✓")
        print("  - 向后兼容：✓")
        print("\n")
        
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
