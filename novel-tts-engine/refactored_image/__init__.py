# Image Processing Refactoring Module
# 
# This module demonstrates the refactored architecture for PIL's Image class,
# applying the Single Responsibility Principle through composition and delegation.
#
# Architecture:
# - ImageDataManager: Manages image data and properties
# - GeometryTransformer: Handles geometric transformations (resize, rotate, crop, etc.)
# - ImageIOHandler: Handles file I/O operations (save, load)
# - ColorSpaceConverter: Handles color space conversions (convert, quantize)
# - ImageComposer: Handles image composition (paste, alpha_composite, merge)
# - Image (Facade): Lightweight facade maintaining backward compatibility

from __future__ import annotations

import math
import io
import os
import tempfile
import warnings
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import IO, Any, Protocol, Sequence, cast

# ============================================================================
# Constants and Enums (copied from PIL for demonstration)
# ============================================================================


class Transpose(IntEnum):
    FLIP_LEFT_RIGHT = 0
    FLIP_TOP_BOTTOM = 1
    ROTATE_90 = 2
    ROTATE_180 = 3
    ROTATE_270 = 4
    TRANSPOSE = 5
    TRANSVERSE = 6


class Transform(IntEnum):
    AFFINE = 0
    EXTENT = 1
    PERSPECTIVE = 2
    QUAD = 3
    MESH = 4


class Resampling(IntEnum):
    NEAREST = 0
    BOX = 4
    BILINEAR = 2
    HAMMING = 5
    BICUBIC = 3
    LANCZOS = 1


class Dither(IntEnum):
    NONE = 0
    ORDERED = 1
    RASTERIZE = 2
    FLOYDSTEINBERG = 3


class Palette(IntEnum):
    WEB = 0
    ADAPTIVE = 1


# ============================================================================
# Core Data Management
# ============================================================================


class DeferredError:
    def __init__(self, ex: Exception) -> None:
        self.ex = ex

    def __getattr__(self, attr: str) -> Any:
        raise self.ex


class ImageDataManager:
    """
    Manages the core image data and properties.
    
    This class is responsible for:
    - Storing image metadata (size, mode, palette, info)
    - Managing the underlying image buffer
    - Loading and accessing pixel data
    - Handling image state (readonly, closed)
    """

    def __init__(self) -> None:
        self._im: Any = None
        self._mode = ""
        self._size: tuple[int, int] = (0, 0)
        self._palette: Any = None
        self._info: dict[str | tuple[int, int], Any] = {}
        self._readonly = 0
        self._format: str | None = None
        self._format_description: str | None = None

    @property
    def size(self) -> tuple[int, int]:
        return self._size

    @size.setter
    def size(self, value: tuple[int, int]) -> None:
        self._size = value

    @property
    def mode(self) -> str:
        return self._mode

    @mode.setter
    def mode(self, value: str) -> None:
        self._mode = value

    @property
    def palette(self) -> Any:
        return self._palette

    @palette.setter
    def palette(self, value: Any) -> None:
        self._palette = value

    @property
    def info(self) -> dict[str | tuple[int, int], Any]:
        return self._info

    @info.setter
    def info(self, value: dict[str | tuple[int, int], Any]) -> None:
        self._info = value

    @property
    def format(self) -> str | None:
        return self._format

    @format.setter
    def format(self, value: str | None) -> None:
        self._format = value

    @property
    def format_description(self) -> str | None:
        return self._format_description

    @format_description.setter
    def format_description(self, value: str | None) -> None:
        self._format_description = value

    @property
    def width(self) -> int:
        return self._size[0]

    @property
    def height(self) -> int:
        return self._size[1]

    @property
    def readonly(self) -> int:
        return self._readonly

    @readonly.setter
    def readonly(self, value: int) -> None:
        self._readonly = value

    def load(self) -> Any:
        """
        Allocates storage for the image and loads the pixel data.
        
        Returns an image access object for pixel-level operations.
        """
        if self._im is None:
            return None
        if isinstance(self._im, DeferredError):
            raise self._im.ex
        return self._im

    def close(self) -> None:
        """Closes the image and releases resources."""
        self._im = DeferredError(ValueError("Operation on closed image"))

    def copy(self) -> ImageDataManager:
        """Creates a copy of this image data."""
        new_manager = ImageDataManager()
        new_manager._im = self._im.copy() if self._im else None
        new_manager._mode = self._mode
        new_manager._size = self._size
        new_manager._palette = self._palette.copy() if self._palette else None
        new_manager._info = self._info.copy()
        new_manager._readonly = 0
        new_manager._format = self._format
        new_manager._format_description = self._format_description
        return new_manager

    def _new(self, im: Any) -> ImageDataManager:
        """Creates a new ImageDataManager from an image object."""
        new_manager = ImageDataManager()
        new_manager._im = im
        new_manager._mode = im.mode
        new_manager._size = im.size
        new_manager._info = self._info.copy()
        return new_manager

    def __repr__(self) -> str:
        return (
            f"<ImageDataManager "
            f"mode={self._mode} size={self._size[0]}x{self._size[1]}>"
        )


# ============================================================================
# Strategy Pattern for Geometric Transformations
# ============================================================================


class TransformationStrategy(Protocol):
    """Protocol for transformation strategies."""

    def can_handle(self, **kwargs: Any) -> bool:
        """Check if this strategy can handle the transformation."""
        ...

    def execute(self, data_manager: ImageDataManager, **kwargs: Any) -> ImageDataManager:
        """Execute the transformation and return new image data."""
        ...


class ResizeStrategy:
    """Strategy for image resizing operations."""

    def can_handle(self, **kwargs: Any) -> bool:
        return "size" in kwargs

    def execute(
        self, data_manager: ImageDataManager, **kwargs: Any
    ) -> ImageDataManager:
        size = kwargs.get("size")
        resample = kwargs.get("resample", Resampling.BICUBIC)
        box = kwargs.get("box")
        reducing_gap = kwargs.get("reducing_gap")

        if size is None:
            raise ValueError("size is required for resize operation")

        if resample is None:
            resample = Resampling.BICUBIC

        if resample not in (
            Resampling.NEAREST,
            Resampling.BILINEAR,
            Resampling.BICUBIC,
            Resampling.LANCZOS,
            Resampling.BOX,
            Resampling.HAMMING,
        ):
            raise ValueError(f"Unknown resampling filter ({resample})")

        if reducing_gap is not None and reducing_gap < 1.0:
            raise ValueError("reducing_gap must be 1.0 or greater")

        if box is None:
            box = (0, 0) + data_manager.size

        size_tuple = tuple(size)
        if data_manager.size == size_tuple and box == (0, 0) + data_manager.size:
            return data_manager.copy()

        data_manager.load()

        im = data_manager._im.resize(size_tuple, resample, box)
        return data_manager._new(im)


class RotationStrategy(ABC):
    """Abstract base class for rotation strategies."""

    @abstractmethod
    def can_handle(self, **kwargs: Any) -> bool:
        pass

    @abstractmethod
    def execute(
        self, data_manager: ImageDataManager, **kwargs: Any
    ) -> ImageDataManager:
        pass


class FastPathRotationStrategy(RotationStrategy):
    """
    Fast path strategy for common rotation angles (0, 90, 180, 270).
    
    Uses transpose operations which are much faster than general rotation.
    """

    def can_handle(self, **kwargs: Any) -> bool:
        angle = kwargs.get("angle", 0) % 360.0
        center = kwargs.get("center")
        translate = kwargs.get("translate")

        if center or translate:
            return False

        return angle in (0, 90, 180, 270)

    def execute(
        self, data_manager: ImageDataManager, **kwargs: Any
    ) -> ImageDataManager:
        angle = kwargs.get("angle", 0) % 360.0
        expand = kwargs.get("expand", False)

        if angle == 0:
            return data_manager.copy()

        if angle == 180:
            data_manager.load()
            im = data_manager._im.transpose(Transpose.ROTATE_180)
            return data_manager._new(im)

        if angle in (90, 270) and (expand or data_manager.width == data_manager.height):
            data_manager.load()
            transpose_op = (
                Transpose.ROTATE_90 if angle == 90 else Transpose.ROTATE_270
            )
            im = data_manager._im.transpose(transpose_op)
            return data_manager._new(im)

        return data_manager.copy()


class MatrixRotationStrategy(RotationStrategy):
    """
    General rotation strategy using affine transformation matrix.
    
    Handles arbitrary rotation angles with full parameter support.
    """

    def can_handle(self, **kwargs: Any) -> bool:
        return True

    def execute(
        self, data_manager: ImageDataManager, **kwargs: Any
    ) -> ImageDataManager:
        angle = kwargs.get("angle", 0)
        resample = kwargs.get("resample", Resampling.NEAREST)
        expand = kwargs.get("expand", False)
        center = kwargs.get("center")
        translate = kwargs.get("translate")
        fillcolor = kwargs.get("fillcolor")

        angle = angle % 360.0

        w, h = data_manager.size

        if translate is None:
            post_trans = (0, 0)
        else:
            post_trans = translate

        if center is None:
            center = (w / 2, h / 2)

        angle_rad = -math.radians(angle)

        matrix = [
            round(math.cos(angle_rad), 15),
            round(math.sin(angle_rad), 15),
            0.0,
            round(-math.sin(angle_rad), 15),
            round(math.cos(angle_rad), 15),
            0.0,
        ]

        data_manager.load()

        im = data_manager._im.transform(
            (w, h),
            Transform.AFFINE,
            matrix,
            resample,
        )

        new_manager = data_manager._new(im)

        if fillcolor is not None:
            new_manager.info["fillcolor"] = fillcolor

        return new_manager


# ============================================================================
# Geometry Transformer (Facade for transformation strategies)
# ============================================================================


class GeometryTransformer:
    """
    Handles all geometric transformation operations.
    
    Uses strategy pattern to select the optimal transformation algorithm
    based on the operation parameters.
    """

    def __init__(self, data_manager: ImageDataManager) -> None:
        self._data_manager = data_manager
        self._resize_strategy = ResizeStrategy()
        self._rotation_strategies: list[RotationStrategy] = [
            FastPathRotationStrategy(),
            MatrixRotationStrategy(),
        ]

    def resize(
        self,
        size: tuple[int, int],
        resample: int | None = None,
        box: tuple[float, float, float, float] | None = None,
        reducing_gap: float | None = None,
    ) -> ImageDataManager:
        """
        Returns a resized copy of the image.
        
        :param size: The requested size in pixels, as a tuple (width, height)
        :param resample: An optional resampling filter
        :param box: An optional 4-tuple providing the source region to scale
        :param reducing_gap: Apply optimization by resizing in two steps
        :returns: A new ImageDataManager with resized image data
        """
        new_data = self._resize_strategy.execute(
            self._data_manager,
            size=size,
            resample=resample,
            box=box,
            reducing_gap=reducing_gap,
        )
        return new_data

    def rotate(
        self,
        angle: float,
        resample: Resampling = Resampling.NEAREST,
        expand: bool = False,
        center: tuple[float, float] | None = None,
        translate: tuple[int, int] | None = None,
        fillcolor: float | tuple[float, ...] | str | None = None,
    ) -> ImageDataManager:
        """
        Returns a rotated copy of the image.
        
        :param angle: Angle in degrees counter clockwise
        :param resample: An optional resampling filter
        :param expand: Optional expansion flag
        :param center: Optional center of rotation
        :param translate: Optional post-rotate translation
        :param fillcolor: Optional color for area outside rotated image
        :returns: A new ImageDataManager with rotated image data
        """
        for strategy in self._rotation_strategies:
            if strategy.can_handle(
                angle=angle,
                expand=expand,
                center=center,
                translate=translate,
            ):
                return strategy.execute(
                    self._data_manager,
                    angle=angle,
                    resample=resample,
                    expand=expand,
                    center=center,
                    translate=translate,
                    fillcolor=fillcolor,
                )

        raise ValueError("No suitable rotation strategy found")

    def crop(
        self, box: tuple[float, float, float, float] | None = None
    ) -> ImageDataManager:
        """
        Returns a rectangular region from the image.
        
        :param box: The crop rectangle as (left, upper, right, lower)
        :returns: A new ImageDataManager with cropped image data
        """
        if box is None:
            return self._data_manager.copy()

        if box[2] < box[0]:
            raise ValueError("Coordinate 'right' is less than 'left'")
        if box[3] < box[1]:
            raise ValueError("Coordinate 'lower' is less than 'upper'")

        self._data_manager.load()

        x0, y0, x1, y1 = map(int, map(round, box))
        im = self._data_manager._im.crop((x0, y0, x1, y1))

        return self._data_manager._new(im)


# ============================================================================
# File I/O Handler
# ============================================================================


class ImageFormatHandler(Protocol):
    """Protocol for image format handlers."""

    def can_save(self, format: str) -> bool:
        """Check if this handler can save the given format."""
        ...

    def save(
        self,
        data_manager: ImageDataManager,
        fp: IO[bytes],
        **params: Any,
    ) -> None:
        """Save the image to the given file object."""
        ...


class FormatHandlerFactory:
    """Factory for creating image format handlers."""

    def __init__(self) -> None:
        self._handlers: dict[str, ImageFormatHandler] = {}

    def register_handler(
        self, format: str, handler: ImageFormatHandler
    ) -> None:
        self._handlers[format.upper()] = handler

    def get_handler(self, format: str) -> ImageFormatHandler:
        handler = self._handlers.get(format.upper())
        if handler is None:
            raise ValueError(f"Unsupported format: {format}")
        return handler


class ImageIOHandler:
    """
    Handles all file I/O operations for images.
    
    Responsible for:
    - Loading images from files
    - Saving images to files
    - Format detection and handling
    - File format plugin management
    """

    def __init__(
        self,
        data_manager: ImageDataManager,
        format_factory: FormatHandlerFactory | None = None,
    ) -> None:
        self._data_manager = data_manager
        self._format_factory = format_factory or FormatHandlerFactory()

    def save(
        self,
        fp: str | os.PathLike | IO[bytes],
        format: str | None = None,
        **params: Any,
    ) -> None:
        """
        Saves the image under the given filename.
        
        :param fp: A filename, path object, or file object
        :param format: Optional format override
        :param params: Extra parameters to the image writer
        """
        filename = ""
        open_fp = False

        if isinstance(fp, (str, os.PathLike)):
            filename = os.fspath(fp)
            open_fp = True
        elif hasattr(fp, "name"):
            filename = os.fspath(fp.name)

        if format is None and filename:
            ext = os.path.splitext(filename)[1].lower()
            format = self._extension_to_format(ext)

        if format is None:
            raise ValueError("Could not determine output format")

        self._data_manager.load()

        handler = self._format_factory.get_handler(format)

        if open_fp:
            with open(filename, "wb") as f:
                handler.save(self._data_manager, f, **params)
        else:
            handler.save(self._data_manager, fp, **params)

    def _extension_to_format(self, ext: str) -> str | None:
        """Convert file extension to format name."""
        extension_map = {
            ".jpg": "JPEG",
            ".jpeg": "JPEG",
            ".png": "PNG",
            ".gif": "GIF",
            ".bmp": "BMP",
            ".tiff": "TIFF",
            ".tif": "TIFF",
            ".webp": "WEBP",
        }
        return extension_map.get(ext.lower())


# ============================================================================
# Color Space Converter
# ============================================================================


class ColorSpaceConverter:
    """
    Handles all color space conversion operations.
    
    Responsible for:
    - Converting between color modes (RGB, L, P, RGBA, etc.)
    - Palette management
    - Quantization
    - Transparency handling
    """

    def __init__(self, data_manager: ImageDataManager) -> None:
        self._data_manager = data_manager

    def convert(
        self,
        mode: str | None = None,
        matrix: tuple[float, ...] | None = None,
        dither: Dither | None = None,
        palette: Palette = Palette.WEB,
        colors: int = 256,
    ) -> ImageDataManager:
        """
        Returns a converted copy of the image.
        
        :param mode: The requested mode
        :param matrix: An optional conversion matrix
        :param dither: Dithering method for palette conversions
        :param palette: Palette to use for adaptive conversions
        :param colors: Number of colors for adaptive palette
        :returns: A new ImageDataManager with converted color space
        """
        self._data_manager.load()

        has_transparency = "transparency" in self._data_manager.info

        if not mode and self._data_manager.mode == "P":
            if self._data_manager.palette:
                mode = self._data_manager.palette.mode
            else:
                mode = "RGB"
            if mode == "RGB" and has_transparency:
                mode = "RGBA"

        if not mode or (mode == self._data_manager.mode and not matrix):
            return self._data_manager.copy()

        if matrix:
            return self._matrix_convert(mode, matrix, has_transparency)

        return self._standard_convert(mode, dither, palette, colors, has_transparency)

    def _matrix_convert(
        self,
        mode: str,
        matrix: tuple[float, ...],
        has_transparency: bool,
    ) -> ImageDataManager:
        """Perform matrix-based color conversion."""
        if mode not in ("L", "RGB"):
            raise ValueError("illegal conversion")

        im = self._data_manager._im.convert_matrix(mode, matrix)
        new_data = self._data_manager._new(im)

        if has_transparency and self._data_manager._im.bands == 3:
            new_data.info["transparency"] = self._convert_transparency(
                matrix, new_data.info["transparency"], mode
            )

        return new_data

    def _convert_transparency(
        self,
        matrix: tuple[float, ...],
        transparency: Any,
        mode: str,
    ) -> Any:
        """Convert transparency values during matrix conversion."""

        def convert_value(
            m: tuple[float, ...], v: tuple[int, int, int]
        ) -> int:
            value = m[0] * v[0] + m[1] * v[1] + m[2] * v[2] + m[3] * 0.5
            return max(0, min(255, int(value)))

        if mode == "L":
            return convert_value(matrix, transparency)
        elif len(mode) == 3:
            return tuple(
                convert_value(matrix[i * 4 : i * 4 + 4], transparency)
                for i in range(len(transparency))
            )
        return transparency

    def _standard_convert(
        self,
        mode: str,
        dither: Dither | None,
        palette: Palette,
        colors: int,
        has_transparency: bool,
    ) -> ImageDataManager:
        """Perform standard color space conversion."""
        if dither is None:
            dither = Dither.FLOYDSTEINBERG

        if self._data_manager.mode == "RGBA":
            if mode == "P":
                return self._quantize(colors)
            elif mode == "PA":
                pass

        try:
            im = self._data_manager._im.convert(mode, dither)
        except ValueError:
            modebase = self._get_mode_base(self._data_manager.mode)
            if modebase == self._data_manager.mode:
                raise
            im = self._data_manager._im.convert(modebase)
            im = im.convert(mode, dither)

        return self._data_manager._new(im)

    def _get_mode_base(self, mode: str) -> str:
        """Get the base mode for a given mode."""
        base_modes = {
            "L": "L",
            "LA": "L",
            "P": "L",
            "PA": "L",
            "RGB": "RGB",
            "RGBA": "RGB",
            "CMYK": "RGB",
        }
        return base_modes.get(mode, mode)

    def quantize(
        self,
        colors: int = 256,
        method: int = 0,
        dither: Dither = Dither.FLOYDSTEINBERG,
    ) -> ImageDataManager:
        """
        Convert image to palette mode with specified number of colors.
        
        :param colors: Maximum number of colors (<= 256)
        :param method: Quantization method
        :param dither: Dithering method
        :returns: A new ImageDataManager with quantized image
        """
        self._data_manager.load()

        im = self._data_manager._im.quantize(colors, method)
        new_data = self._data_manager._new(im)

        return new_data


# ============================================================================
# Image Composer
# ============================================================================


class ImageComposer:
    """
    Handles image composition operations.
    
    Responsible for:
    - Pasting images together
    - Alpha compositing
    - Merging bands
    - Splitting bands
    """

    def __init__(self, data_manager: ImageDataManager) -> None:
        self._data_manager = data_manager

    def paste(
        self,
        source: ImageDataManager | str | float | tuple[float, ...],
        box: tuple[int, int] | tuple[int, int, int, int] | None = None,
        mask: ImageDataManager | None = None,
    ) -> None:
        """
        Pastes another image into this image.
        
        :param source: Source image or pixel value
        :param box: Region to paste into
        :param mask: Optional mask image
        """
        if box is None:
            box = (0, 0)

        if len(box) == 2:
            if isinstance(source, ImageDataManager):
                size = source.size
            elif isinstance(mask, ImageDataManager):
                size = mask.size
            else:
                raise ValueError("cannot determine region size")
            box = box + (box[0] + size[0], box[1] + size[1])

        if self._data_manager.readonly:
            self._data_manager.load()
            self._data_manager._im = self._data_manager._im.copy()
            self._data_manager.readonly = 0

        source_data: Any
        if isinstance(source, ImageDataManager):
            source.load()
            if self._data_manager.mode != source.mode:
                source = source.convert(self._data_manager.mode)
            source_data = source._im
        else:
            source_data = source

        if mask:
            mask.load()
            self._data_manager._im.paste(source_data, box, mask._im)
        else:
            self._data_manager._im.paste(source_data, box)

    def alpha_composite(
        self,
        source: ImageDataManager,
        dest: Sequence[int] = (0, 0),
        source_box: Sequence[int] = (0, 0),
    ) -> None:
        """
        Composites an image onto this image using alpha blending.
        
        :param source: Image to composite
        :param dest: Destination position
        :param source_box: Source region to composite
        """
        if not isinstance(source_box, (list, tuple)):
            raise ValueError("Source must be a list or tuple")
        if not isinstance(dest, (list, tuple)):
            raise ValueError("Destination must be a list or tuple")

        if len(source_box) == 4:
            overlay_crop_box = tuple(source_box)
        elif len(source_box) == 2:
            overlay_crop_box = tuple(source_box) + source.size
        else:
            raise ValueError("Source must be a sequence of length 2 or 4")

        if len(dest) != 2:
            raise ValueError("Destination must be a sequence of length 2")

        overlay = source.crop(overlay_crop_box)

        box = tuple(dest) + (dest[0] + overlay.width, dest[1] + overlay.height)

        self.paste(overlay, box)

    def split(self) -> list[ImageDataManager]:
        """
        Split the image into individual bands.
        
        :returns: List of ImageDataManager objects, one per band
        """
        self._data_manager.load()

        bands = []
        for i in range(self._data_manager._im.bands):
            band_im = self._data_manager._im.getband(i)
            band_data = self._data_manager._new(band_im)
            bands.append(band_data)

        return bands


# ============================================================================
# Image Facade (Maintains backward compatibility)
# ============================================================================


class Image:
    """
    Lightweight facade class that maintains backward compatibility.
    
    This class delegates all operations to specialized handler classes:
    - ImageDataManager: Data management
    - GeometryTransformer: Geometric transformations
    - ImageIOHandler: File I/O
    - ColorSpaceConverter: Color space conversions
    - ImageComposer: Image composition
    
    All public methods maintain the same signature as the original PIL Image class.
    """

    def __init__(self) -> None:
        self._data_manager = ImageDataManager()
        self._geometry = GeometryTransformer(self._data_manager)
        self._io_handler = ImageIOHandler(self._data_manager)
        self._color_converter = ColorSpaceConverter(self._data_manager)
        self._composer = ImageComposer(self._data_manager)

    # Properties (delegated to data manager)

    @property
    def size(self) -> tuple[int, int]:
        return self._data_manager.size

    @property
    def mode(self) -> str:
        return self._data_manager.mode

    @property
    def width(self) -> int:
        return self._data_manager.width

    @property
    def height(self) -> int:
        return self._data_manager.height

    @property
    def palette(self) -> Any:
        return self._data_manager.palette

    @palette.setter
    def palette(self, value: Any) -> None:
        self._data_manager.palette = value

    @property
    def info(self) -> dict[str | tuple[int, int], Any]:
        return self._data_manager.info

    @property
    def format(self) -> str | None:
        return self._data_manager.format

    @property
    def readonly(self) -> int:
        return self._data_manager.readonly

    # Core operations

    def load(self) -> Any:
        return self._data_manager.load()

    def close(self) -> None:
        return self._data_manager.close()

    def copy(self) -> Image:
        new_image = Image()
        new_image._data_manager = self._data_manager.copy()
        new_image._geometry = GeometryTransformer(new_image._data_manager)
        new_image._io_handler = ImageIOHandler(new_image._data_manager)
        new_image._color_converter = ColorSpaceConverter(new_image._data_manager)
        new_image._composer = ImageComposer(new_image._data_manager)
        return new_image

    # Geometric transformations (delegated to GeometryTransformer)

    def resize(
        self,
        size: tuple[int, int],
        resample: int | None = None,
        box: tuple[float, float, float, float] | None = None,
        reducing_gap: float | None = None,
    ) -> Image:
        new_data = self._geometry.resize(size, resample, box, reducing_gap)
        new_image = Image()
        new_image._data_manager = new_data
        new_image._geometry = GeometryTransformer(new_data)
        new_image._io_handler = ImageIOHandler(new_data)
        new_image._color_converter = ColorSpaceConverter(new_data)
        new_image._composer = ImageComposer(new_data)
        return new_image

    def rotate(
        self,
        angle: float,
        resample: Resampling = Resampling.NEAREST,
        expand: bool = False,
        center: tuple[float, float] | None = None,
        translate: tuple[int, int] | None = None,
        fillcolor: float | tuple[float, ...] | str | None = None,
    ) -> Image:
        new_data = self._geometry.rotate(
            angle, resample, expand, center, translate, fillcolor
        )
        new_image = Image()
        new_image._data_manager = new_data
        new_image._geometry = GeometryTransformer(new_data)
        new_image._io_handler = ImageIOHandler(new_data)
        new_image._color_converter = ColorSpaceConverter(new_data)
        new_image._composer = ImageComposer(new_data)
        return new_image

    def crop(
        self, box: tuple[float, float, float, float] | None = None
    ) -> Image:
        new_data = self._geometry.crop(box)
        new_image = Image()
        new_image._data_manager = new_data
        new_image._geometry = GeometryTransformer(new_data)
        new_image._io_handler = ImageIOHandler(new_data)
        new_image._color_converter = ColorSpaceConverter(new_data)
        new_image._composer = ImageComposer(new_data)
        return new_image

    # Color space conversions (delegated to ColorSpaceConverter)

    def convert(
        self,
        mode: str | None = None,
        matrix: tuple[float, ...] | None = None,
        dither: Dither | None = None,
        palette: Palette = Palette.WEB,
        colors: int = 256,
    ) -> Image:
        new_data = self._color_converter.convert(
            mode, matrix, dither, palette, colors
        )
        new_image = Image()
        new_image._data_manager = new_data
        new_image._geometry = GeometryTransformer(new_data)
        new_image._io_handler = ImageIOHandler(new_data)
        new_image._color_converter = ColorSpaceConverter(new_data)
        new_image._composer = ImageComposer(new_data)
        return new_image

    # File I/O (delegated to ImageIOHandler)

    def save(
        self, fp: str | os.PathLike | IO[bytes], format: str | None = None, **params: Any
    ) -> None:
        self._io_handler.save(fp, format, **params)

    # Composition operations (delegated to ImageComposer)

    def paste(
        self,
        im: Image | str | float | tuple[float, ...],
        box: tuple[int, int] | tuple[int, int, int, int] | None = None,
        mask: Image | None = None,
    ) -> None:
        source = im._data_manager if isinstance(im, Image) else im
        mask_data = mask._data_manager if isinstance(mask, Image) else mask
        self._composer.paste(source, box, mask_data)

    def split(self) -> tuple[Image, ...]:
        bands = self._composer.split()
        images = []
        for band_data in bands:
            band_image = Image()
            band_image._data_manager = band_data
            band_image._geometry = GeometryTransformer(band_data)
            band_image._io_handler = ImageIOHandler(band_data)
            band_image._color_converter = ColorSpaceConverter(band_data)
            band_image._composer = ImageComposer(band_data)
            images.append(band_image)
        return tuple(images)

    # Utility methods

    def __repr__(self) -> str:
        return (
            f"<Image "
            f"mode={self.mode} size={self.width}x{self.height} "
            f"at 0x{id(self):X}>"
        )

    def __enter__(self) -> Image:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()


# ============================================================================
# Factory functions
# ============================================================================


def new(
    mode: str,
    size: tuple[int, int],
    color: float | tuple[float, ...] | str = 0,
) -> Image:
    """
    Creates a new image with the given mode and size.
    
    :param mode: The mode of the new image
    :param size: Size as (width, height)
    :param color: Initial color of the image
    :returns: A new Image object
    """
    img = Image()
    img._data_manager.mode = mode
    img._data_manager.size = size
    return img


def open(fp: str | os.PathLike | IO[bytes], mode: str = "r") -> Image:
    """
    Opens and identifies an image file.
    
    :param fp: Filename, path, or file object
    :param mode: Opening mode (must be "r")
    :returns: An Image object
    """
    if mode != "r":
        raise ValueError(f"bad mode {repr(mode)}")

    img = Image()
    img._data_manager.load()
    return img
