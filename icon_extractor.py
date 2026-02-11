"""
Entropia Universe Icon Extractor
A standalone tool for extracting game icons from cache.

Description: Extracts item icons from Entropia Universe game cache and converts
them to PNG format for use with EntropiaNexus.com wiki submissions.

Important: Items must be seen/rendered in-game before they appear in the cache.

Usage:
    python standalone_icon_extractor.py

Output Location:
    Icons are saved to your Documents/Entropia Universe/Icons/ folder
    (same location where chat.log is normally stored)

Developer: ImpulsiveFPS
Discord: impulsivefps
Website: https://EntropiaNexus.com

Disclaimer:
    Entropia Universe Icon Extractor is a fan-made resource and is not 
    affiliated with MindArk PE AB. Entropia Universe is a trademark of 
    MindArk PE AB.
"""

import sys
import logging
from pathlib import Path
from typing import Optional, List, Tuple
import ctypes

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem,
        QFileDialog, QProgressBar, QGroupBox, QMessageBox, QCheckBox,
                QSplitter, QTextEdit, QDialog, QScrollArea, QFrame
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings, QSize
    from PyQt6.QtGui import QIcon, QPixmap, QFont, QImage
    PYQT_AVAILABLE = True
except ImportError:
    PYQT_AVAILABLE = False
    print("PyQt6 not available. Install with: pip install PyQt6")
    sys.exit(1)

try:
    from PIL import Image, ImageFilter
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("Pillow not available. Install with: pip install Pillow")
    sys.exit(1)

import numpy as np

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Application metadata
APP_NAME = "Entropia Universe Icon Extractor"
APP_VERSION = "1.0.0"
DEVELOPER = "ImpulsiveFPS"
DISCORD = "impulsivefps"
WEBSITE = "https://EntropiaNexus.com"


class TGAHeader:
    """TGA file header structure."""
    def __init__(self, data: bytes):
        self.id_length = data[0]
        self.color_map_type = data[1]
        self.image_type = data[2]
        self.color_map_origin = int.from_bytes(data[3:5], 'little')
        self.color_map_length = int.from_bytes(data[5:7], 'little')
        self.color_map_depth = data[7]
        self.x_origin = int.from_bytes(data[8:10], 'little')
        self.y_origin = int.from_bytes(data[10:12], 'little')
        self.width = int.from_bytes(data[12:14], 'little')
        self.height = int.from_bytes(data[14:16], 'little')
        self.pixel_depth = data[16]
        self.image_descriptor = data[17]
    
    def __str__(self):
        return f"{self.width}x{self.height}, {self.pixel_depth}bpp"


class TGAConverter:
    """Converter for TGA files to PNG with 320x320 canvas."""
    
    CANVAS_SIZE = (320, 320)  # Hardcoded to 320x320
    
    def __init__(self, output_dir: Optional[Path] = None):
        # Default to user's Documents/Entropia Universe/Icons/
        # This works on any Windows username
        if output_dir is None:
            self.output_dir = Path.home() / "Documents" / "Entropia Universe" / "Icons"
        else:
            self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._cache_path: Optional[Path] = None
    
    def find_cache_folder(self) -> Optional[Path]:
        """Find the Entropia Universe icon cache folder."""
        # Hardcoded path - works on any system with EU installed
        cache_path = Path("C:/ProgramData/Entropia Universe/public_users_data/cache/icon")
        
        if cache_path.exists():
            self._cache_path = cache_path
            return cache_path
        
        return None
    
    def read_tga_header(self, filepath: Path) -> Optional[TGAHeader]:
        """Read TGA header from file."""
        try:
            with open(filepath, 'rb') as f:
                header_data = f.read(18)
                if len(header_data) < 18:
                    return None
                return TGAHeader(header_data)
        except Exception as e:
            logger.error(f"Error reading TGA header: {e}")
            return None
    
    def load_tga_image(self, filepath: Path) -> Optional[Image.Image]:
        """Load a TGA file as PIL Image."""
        try:
            image = Image.open(filepath)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            return image
        except Exception as e:
            logger.error(f"Error loading TGA: {e}")
            return None
    
    def convert_tga_to_png(self, tga_path: Path, output_name: Optional[str] = None) -> Optional[Path]:
        """
        Convert a TGA file to PNG with 320x320 canvas.
        
        Args:
            tga_path: Path to TGA file
            output_name: Optional custom output name
            
        Returns:
            Path to output PNG file or None if failed
        """
        try:
            # Load TGA
            image = self.load_tga_image(tga_path)
            if not image:
                return None
            
            # Apply 320x320 canvas (centered, no upscaling)
            image = self._apply_canvas(image)
            
            # Save
            if output_name is None:
                output_name = tga_path.stem
            
            output_path = self.output_dir / f"{output_name}.png"
            image.save(output_path, 'PNG')
            
            return output_path
            
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return None
    
    def _apply_canvas(self, image: Image.Image) -> Image.Image:
        """
        Place image centered on a 320x320 canvas.
        No upscaling - original size centered on canvas.
        """
        canvas_w, canvas_h = self.CANVAS_SIZE
        img_w, img_h = image.size
        
        # Create transparent canvas
        canvas = Image.new('RGBA', self.CANVAS_SIZE, (0, 0, 0, 0))
        
        # Center on canvas (no scaling)
        x = (canvas_w - img_w) // 2
        y = (canvas_h - img_h) // 2
        
        canvas.paste(image, (x, y), image if image.mode == 'RGBA' else None)
        return canvas


class ConversionWorker(QThread):
    """Background worker for batch conversion."""
    progress = pyqtSignal(str)
    file_done = pyqtSignal(str, str)  # filename, output_path
    finished = pyqtSignal(int, int)  # success, total
    error = pyqtSignal(str)
    
    def __init__(self, files: List[Path], converter: TGAConverter):
        super().__init__()
        self.files = files
        self.converter = converter
        self._running = True
    
    def run(self):
        """Run conversion."""
        try:
            success = 0
            total = len(self.files)
            
            for i, filepath in enumerate(self.files):
                if not self._running:
                    break
                
                self.progress.emit(f"[{i+1}/{total}] {filepath.name}")
                
                output = self.converter.convert_tga_to_png(filepath)
                
                if output:
                    success += 1
                    self.file_done.emit(filepath.name, str(output))
            
            self.finished.emit(success, total)
            
        except Exception as e:
            self.error.emit(str(e))
    
    def stop(self):
        self._running = False


class PreviewDialog(QDialog):
    """Dialog to preview a TGA file."""
    
    def __init__(self, tga_path: Path, converter: TGAConverter, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Preview: {tga_path.name}")
        self.setMinimumSize(400, 450)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Info
        info = converter.read_tga_header(tga_path)
        if info:
            info_label = QLabel(f"Original: {info.width}x{info.height}, {info.pixel_depth}bpp")
            info_label.setStyleSheet("color: #888; font-size: 12px;")
            layout.addWidget(info_label)
        
        # Load and display TGA
        image = converter.load_tga_image(tga_path)
        if image:
            # Convert to QPixmap
            img_data = image.tobytes("raw", "RGBA")
            qimage = QImage(img_data, image.width, image.height, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimage)
            
            # Scale for display (max 320x320)
            scaled = pixmap.scaled(320, 320, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
            
            img_label = QLabel()
            img_label.setPixmap(scaled)
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setStyleSheet("background-color: #2a2a2a; border: 1px solid #444; padding: 10px;")
            layout.addWidget(img_label)
            
            size_label = QLabel(f"Displayed at: {scaled.width()}x{scaled.height()}")
            size_label.setStyleSheet("color: #888; font-size: 11px;")
            size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(size_label)
        else:
            error_label = QLabel("Failed to load image")
            error_label.setStyleSheet("color: #f44336;")
            layout.addWidget(error_label)
        
        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class IconExtractorWindow(QMainWindow):
    """Main window for the standalone icon extractor."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(1050, 850)
        self.resize(1150, 900)
        
        self.converter = TGAConverter()
        self.worker: Optional[ConversionWorker] = None
        self.found_files: List[Path] = []
        
        # Hardcoded base cache path
        self.base_cache_path = Path("C:/ProgramData/Entropia Universe/public_users_data/cache/icon")
        
        self.settings = QSettings("ImpulsiveFPS", "EUIconExtractor")
        
        self._setup_ui()
        self._load_icon()
        self._load_settings()
        self._detect_subfolders()
    
    def _setup_ui(self):
        """Setup the UI."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header with icon
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        
        # Icon label (will be set if icon exists)
        self.header_icon = QLabel()
        self.header_icon.setFixedSize(48, 48)
        self.header_icon.setStyleSheet("background: transparent;")
        header_layout.addWidget(self.header_icon)
        
        # Title
        header = QLabel("Entropia Universe Icon Extractor")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #4caf50;")
        header_layout.addWidget(header, 1)
        
        # Theme toggle button
        self.theme_btn = QPushButton("☀️ Light")
        self.theme_btn.setMaximumWidth(80)
        self.theme_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        self.theme_btn.setCheckable(True)
        self.theme_btn.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_btn)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # Description - two lines with clickable link
        desc_widget = QWidget()
        desc_layout = QVBoxLayout(desc_widget)
        desc_layout.setContentsMargins(5, 5, 5, 5)
        desc_layout.setSpacing(4)
        
        desc_line1 = QLabel("Extract the item icons from Entropia Universe cache and convert them to PNG.")
        desc_line1.setStyleSheet("color: #cccccc; font-size: 13px;")
        desc_layout.addWidget(desc_line1)
        
        desc_line2 = QLabel("You can submit these to ")
        desc_line2.setStyleSheet("color: #cccccc; font-size: 13px;")
        desc_line2.setOpenExternalLinks(True)
        
        # Clickable link
        link_label = QLabel('<a href="https://EntropiaNexus.com" style="color: #4caf50;">EntropiaNexus.com</a> to help complete the item database.')
        link_label.setStyleSheet("font-size: 13px;")
        link_label.setOpenExternalLinks(True)
        
        desc_line2_layout = QHBoxLayout()
        desc_line2_layout.setContentsMargins(0, 0, 0, 0)
        desc_line2_layout.addWidget(desc_line2)
        desc_line2_layout.addWidget(link_label)
        desc_line2_layout.addStretch()
        desc_layout.addLayout(desc_line2_layout)
        
        layout.addWidget(desc_widget)
        
        # Cache and Output side by side
        top_row = QWidget()
        top_row_layout = QHBoxLayout(top_row)
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(15)
        
        # Cache folder
        cache_group = QGroupBox("📂 Cache Source")
        cache_group.setStyleSheet("QGroupBox { font-size: 13px; font-weight: bold; }")
        cache_layout = QVBoxLayout(cache_group)
        cache_layout.setContentsMargins(12, 18, 12, 12)
        cache_layout.setSpacing(10)
        
        # Base path (hardcoded) - show just the end part
        path_display = "...\\Entropia Universe\\public_users_data\\cache\\icon"
        self.cache_path_full = str(self.base_cache_path).replace("/", "\\")
        self.cache_label = QLabel(path_display)
        self.cache_label.setStyleSheet(
            "font-family: Consolas; font-size: 10px; color: #aaa; "
            "padding: 6px 8px; background: #252525; border-radius: 3px;"
        )
        self.cache_label.setToolTip(self.cache_path_full)
        cache_layout.addWidget(self.cache_label)
        
        # Subfolder selector
        subfolder_layout = QHBoxLayout()
        subfolder_layout.setSpacing(8)
        
        subfolder_label = QLabel("📁 Version:")
        subfolder_label.setStyleSheet("font-size: 12px;")
        subfolder_layout.addWidget(subfolder_label)
        
        self.subfolder_combo = QComboBox()
        self.subfolder_combo.setMinimumWidth(180)
        self.subfolder_combo.setStyleSheet("font-size: 12px; padding: 3px;")
        self.subfolder_combo.currentIndexChanged.connect(self._on_subfolder_changed)
        subfolder_layout.addWidget(self.subfolder_combo, 1)
        
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setMaximumWidth(80)
        refresh_btn.setStyleSheet("font-size: 11px; padding: 4px;")
        refresh_btn.clicked.connect(self._detect_subfolders)
        subfolder_layout.addWidget(refresh_btn)
        
        cache_layout.addLayout(subfolder_layout)
        top_row_layout.addWidget(cache_group, 1)
        
        # Output folder
        output_group = QGroupBox("💾 Output Location")
        output_group.setStyleSheet("QGroupBox { font-size: 13px; font-weight: bold; }")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(12, 18, 12, 12)
        output_layout.setSpacing(10)
        
        output_info = QLabel("📁 Icons saved to your Documents folder (same location as chat.log)")
        output_info.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        output_info.setWordWrap(True)
        output_layout.addWidget(output_info)
        
        rel_path = "Documents\\Entropia Universe\\Icons\\"
        self.output_label = QLabel(f"📂 {rel_path}")
        self.output_label.setStyleSheet(
            "font-family: Consolas; font-size: 10px; color: #aaa; "
            "padding: 6px 8px; background: #252525; border-radius: 3px;"
        )
        output_layout.addWidget(self.output_label)
        
        change_btn = QPushButton("📂 Change Output Folder...")
        change_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        change_btn.clicked.connect(self._browse_output)
        output_layout.addWidget(change_btn)
        
        top_row_layout.addWidget(output_group, 1)
        layout.addWidget(top_row)
        
        # Available Icons (full width below)
        files_group = QGroupBox("📄 Available Icons")
        files_group.setStyleSheet("QGroupBox { font-size: 13px; font-weight: bold; }")
        files_layout = QVBoxLayout(files_group)
        files_layout.setContentsMargins(12, 18, 12, 12)
        files_layout.setSpacing(10)
        
        files_info = QLabel("💡 Double-click an icon to preview. Select icons to extract (or leave blank for all).")
        files_info.setStyleSheet("color: #aaaaaa; font-size: 12px;")
        files_layout.addWidget(files_info)
        
        self.files_count_label = QLabel("❓ No files found")
        self.files_count_label.setStyleSheet("font-weight: bold; font-size: 12px; padding: 3px 0;")
        files_layout.addWidget(self.files_count_label)
        
        self.files_list = QListWidget()
        self.files_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        self.files_list.setStyleSheet("font-size: 12px; padding: 2px;")
        self.files_list.doubleClicked.connect(self._on_file_double_clicked)
        files_layout.addWidget(self.files_list, 1)
        
        layout.addWidget(files_group, 1)
        
        # Bottom buttons row
        bottom_layout = QHBoxLayout()
        bottom_layout.setSpacing(15)
        
        # Select buttons
        select_all_btn = QPushButton("☑️ Select All")
        select_all_btn.setMaximumWidth(100)
        select_all_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        select_all_btn.clicked.connect(self.files_list.selectAll)
        bottom_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("⬜ Select None")
        select_none_btn.setMaximumWidth(100)
        select_none_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        select_none_btn.clicked.connect(self.files_list.clearSelection)
        bottom_layout.addWidget(select_none_btn)
        
        bottom_layout.addStretch()
        
        # Open Output Folder button
        open_folder_btn = QPushButton("📂 Open Output Folder")
        open_folder_btn.setMaximumWidth(150)
        open_folder_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        open_folder_btn.clicked.connect(self._open_output_folder)
        bottom_layout.addWidget(open_folder_btn)
        
        # Main action button
        self.convert_btn = QPushButton("▶️ Start Extracting Icons")
        self.convert_btn.setMinimumHeight(55)
        self.convert_btn.setMinimumWidth(200)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #1565c0;
                font-weight: bold;
                font-size: 14px;
                border-radius: 5px;
                padding: 12px;
                color: white;
            }
            QPushButton:hover { background-color: #1976d2; }
            QPushButton:disabled { background-color: #424242; color: #888; }
        """)
        self.convert_btn.clicked.connect(self._start_conversion)
        bottom_layout.addWidget(self.convert_btn)
        
        layout.addLayout(bottom_layout)
        
        # Progress
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet("font-size: 11px;")
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("✅ Ready")
        self.status_label.setStyleSheet("color: #888; font-size: 12px; padding: 5px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Important Information (moved to bottom)
        notice_group = QGroupBox("⚠️ Important Information")
        notice_group.setStyleSheet("""
            QGroupBox { 
                font-size: 13px; 
                font-weight: bold; 
                color: #ff9800;
            }
        """)
        notice_layout = QVBoxLayout(notice_group)
        notice_layout.setContentsMargins(10, 15, 10, 10)
        
        notice_text = QTextEdit()
        notice_text.setReadOnly(True)
        notice_text.setMaximumHeight(70)
        notice_text.setStyleSheet("""
            QTextEdit {
                background-color: #2d2818;
                color: #ffc107;
                border: 1px solid #5d4e37;
                border-radius: 3px;
                font-size: 12px;
                padding: 8px;
                line-height: 1.4;
            }
        """)
        notice_text.setText(
            "REQUIREMENT: Items must be seen in-game before they appear in the cache! "
            "If an icon is missing, view the item in your inventory or the auction first. "
            "Output: Documents/Entropia Universe/Icons/"
        )
        notice_layout.addWidget(notice_text)
        layout.addWidget(notice_group)
        
        # Footer with clickable links (no emojis)
        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(10, 10, 10, 10)
        footer_layout.setSpacing(5)
        
        # First line - developer info (no emojis)
        footer_line1 = QLabel(f"Developed by {DEVELOPER} | Discord: {DISCORD} | GitHub: (coming soon)")
        footer_line1.setStyleSheet("color: #888; font-size: 11px;")
        footer_line1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_layout.addWidget(footer_line1)
        
        # Second line - disclaimer with links (no emojis)
        disclaimer_widget = QWidget()
        disclaimer_layout = QHBoxLayout(disclaimer_widget)
        disclaimer_layout.setContentsMargins(0, 0, 0, 0)
        disclaimer_layout.setSpacing(0)
        
        label1 = QLabel("Entropia Universe Icon Extractor is a fan-made resource and is not affiliated with ")
        label1.setStyleSheet("color: #666; font-size: 10px;")
        label1.setOpenExternalLinks(True)
        
        mindark_link = QLabel('<a href="https://www.mindark.com/" style="color: #888;">MindArk PE AB</a>. ')
        mindark_link.setStyleSheet("color: #666; font-size: 10px;")
        mindark_link.setOpenExternalLinks(True)
        
        eu_link = QLabel('<a href="https://www.entropiauniverse.com/" style="color: #888;">Entropia Universe</a>')
        eu_link.setStyleSheet("color: #666; font-size: 10px;")
        eu_link.setOpenExternalLinks(True)
        
        label3 = QLabel(" is a trademark of MindArk PE AB.")
        label3.setStyleSheet("color: #666; font-size: 10px;")
        
        disclaimer_layout.addStretch()
        disclaimer_layout.addWidget(label1)
        disclaimer_layout.addWidget(mindark_link)
        disclaimer_layout.addWidget(eu_link)
        disclaimer_layout.addWidget(label3)
        disclaimer_layout.addStretch()
        
        footer_layout.addWidget(disclaimer_widget)
        layout.addWidget(footer_widget)
    
    def _on_file_double_clicked(self, index):
        """Handle double-click on file to preview."""
        item = self.files_list.item(index.row())
        if item:
            filepath = Path(item.data(Qt.ItemDataRole.UserRole))
            self._preview_file(filepath)
    
    def _preview_file(self, filepath: Path):
        """Open preview dialog for a TGA file."""
        dialog = PreviewDialog(filepath, self.converter, self)
        dialog.exec()
    
    def _open_url(self, url: str):
        """Open URL in default browser."""
        import webbrowser
        webbrowser.open(url)
    
    def _load_icon(self):
        """Load and set the application icon."""
        # Try to load icon from various locations
        icon_paths = [
            Path(__file__).parent / "assets" / "icon.ico",
            Path(__file__).parent / "assets" / "icon.png",
            Path(__file__).parent / "icon.ico",
            Path(__file__).parent / "icon.png",
        ]
        
        for icon_path in icon_paths:
            if icon_path.exists():
                pixmap = QPixmap(str(icon_path))
                if not pixmap.isNull():
                    # Set window icon
                    self.setWindowIcon(QIcon(pixmap))
                    # Set header icon (scaled to 48x48)
                    header_pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                    self.header_icon.setPixmap(header_pixmap)
                    return True
        
        # Hide header icon if no icon found
        self.header_icon.hide()
        return False
    
    def _toggle_theme(self):
        """Toggle between light and dark theme."""
        if self.theme_btn.isChecked():
            self._apply_light_theme()
            self.theme_btn.setText("🌙 Dark")
        else:
            self._apply_dark_theme()
            self.theme_btn.setText("☀️ Light")
    
    def _apply_dark_theme(self):
        """Apply dark theme."""
        self.setStyleSheet("""
            QMainWindow, QDialog {
                background-color: #1e1e1e;
            }
            QWidget {
                background-color: #1e1e1e;
                color: #e0e0e0;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #404040;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
            QPushButton {
                background-color: #3d3d3d;
                border: 1px solid #555;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #4d4d4d;
            }
            QComboBox {
                background-color: #2d2d2d;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 4px;
            }
            QListWidget {
                background-color: #252525;
                border: 1px solid #404040;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 6px;
            }
            QListWidget::item:selected {
                background-color: #1565c0;
            }
            QListWidget::item:hover {
                background-color: #2a4d6e;
            }
            QProgressBar {
                border: 1px solid #404040;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4caf50;
            }
            QTextEdit {
                background-color: #252525;
                border: 1px solid #404040;
            }
            QCheckBox {
                font-size: 12px;
            }
            QLabel {
                font-size: 12px;
            }
        """)
    
    def _apply_light_theme(self):
        """Apply light theme."""
        self.setStyleSheet("""
            QMainWindow, QDialog {
                background-color: #f5f5f5;
            }
            QWidget {
                background-color: #f5f5f5;
                color: #333333;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #cccccc;
                border-radius: 6px;
                margin-top: 12px;
                padding-top: 12px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
            }
            QPushButton {
                background-color: #e0e0e0;
                border: 1px solid #bbbbbb;
                padding: 6px 12px;
                border-radius: 4px;
                font-size: 12px;
                color: #333333;
            }
            QPushButton:hover {
                background-color: #d0d0d0;
            }
            QComboBox {
                background-color: #ffffff;
                border: 1px solid #bbbbbb;
                padding: 5px;
                border-radius: 4px;
                color: #333333;
            }
            QListWidget {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                border-radius: 4px;
            }
            QListWidget::item {
                padding: 6px;
                color: #333333;
            }
            QListWidget::item:selected {
                background-color: #1976d2;
                color: #ffffff;
            }
            QListWidget::item:hover {
                background-color: #e3f2fd;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4caf50;
            }
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #cccccc;
                color: #333333;
            }
            QCheckBox {
                font-size: 12px;
            }
            QLabel {
                font-size: 12px;
            }
        """)
    
    def _load_settings(self):
        """Load saved settings."""
        # Output folder
        saved_output = self.settings.value("output_dir", str(self.converter.output_dir))
        self.converter.output_dir = Path(saved_output)
        self.output_label.setText("Documents\\Entropia Universe\\Icons\\")
    
    def _save_settings(self):
        """Save current settings."""
        self.settings.setValue("output_dir", str(self.converter.output_dir))
    
    def _detect_subfolders(self):
        """Detect version subfolders in the cache directory."""
        self.subfolder_combo.clear()
        
        if not self.base_cache_path.exists():
            self.cache_label.setText(f"Not found: {self.base_cache_path}")
            self.status_label.setText("Cache folder not found - is Entropia Universe installed?")
            return
        
        # Find all subfolders that contain TGA files
        subfolders = []
        for item in self.base_cache_path.iterdir():
            if item.is_dir():
                # Check if this folder has TGA files
                tga_count = len(list(item.glob("*.tga")))
                if tga_count > 0:
                    subfolders.append((item.name, tga_count, item))
        
        if not subfolders:
            self.cache_label.setText(f"No subfolders with icons in {self.base_cache_path}")
            self.status_label.setText("No version folders found")
            return
        
        # Sort by name (version)
        subfolders.sort(key=lambda x: x[0])
        
        # Add to combo
        for name, count, path in subfolders:
            self.subfolder_combo.addItem(f"{name} ({count} icons)", str(path))
        
        # Add "All folders" option at top
        total_icons = sum(s[1] for s in subfolders)
        self.subfolder_combo.insertItem(0, f"All Folders ({total_icons} icons)", "all")
        self.subfolder_combo.setCurrentIndex(0)
        
        self.cache_label.setText(f"{self.base_cache_path}")
        self.status_label.setText(f"Found {len(subfolders)} version folders")
        
        # Load files
        self._refresh_file_list()
    
    def _on_subfolder_changed(self):
        """Handle subfolder selection change."""
        self._refresh_file_list()
    
    def _browse_output(self):
        """Browse for output folder."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Output Folder",
            str(self.converter.output_dir)
        )
        
        if folder:
            self.converter.output_dir = Path(folder)
            rel_path = "Documents/Entropia Universe/Icons/"
            self.output_label.setText(rel_path)
            self._save_settings()
    
    def _refresh_file_list(self):
        """Refresh the list of found files based on current selection."""
        self.files_list.clear()
        self.found_files = []
        
        if not self.base_cache_path.exists():
            return
        
        # Determine which folders to scan based on dropdown selection
        path_data = self.subfolder_combo.currentData()
        if path_data == "all" or path_data is None:
            # Scan all subfolders
            folders_to_scan = [d for d in self.base_cache_path.iterdir() if d.is_dir()]
        else:
            # Scan selected subfolder
            folders_to_scan = [Path(path_data)]
        
        # Collect TGA files
        tga_files = []
        for folder in folders_to_scan:
            if folder.exists():
                tga_files.extend(folder.glob("*.tga"))
        
        self.files_count_label.setText(f"Found {len(tga_files)} icon files")
        self.status_label.setText(f"Found {len(tga_files)} files")
        
        for tga_file in sorted(tga_files):
            # Show folder prefix for clarity
            try:
                rel_path = f"{tga_file.parent.name}/{tga_file.name}"
            except:
                rel_path = tga_file.name
            
            item = QListWidgetItem(rel_path)
            item.setData(Qt.ItemDataRole.UserRole, str(tga_file))
            
            # Get info
            header = self.converter.read_tga_header(tga_file)
            if header:
                item.setToolTip(f"Double-click to preview\n{header.width}x{header.height}, {header.pixel_depth}bpp")
            else:
                item.setToolTip("Double-click to preview")
            
            self.files_list.addItem(item)
            self.found_files.append(tga_file)
        
        self.convert_btn.setEnabled(len(tga_files) > 0)
    
    def _start_conversion(self):
        """Start batch conversion."""
        # Get selected files or all files
        selected_items = self.files_list.selectedItems()
        if selected_items:
            files_to_convert = [
                Path(item.data(Qt.ItemDataRole.UserRole))
                for item in selected_items
            ]
        else:
            files_to_convert = self.found_files
        
        if not files_to_convert:
            QMessageBox.warning(self, "No Files", "No files selected for extraction.")
            return
        
        # Save settings
        self._save_settings()
        
        # Setup UI
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("Extracting...")
        self.progress_bar.setRange(0, len(files_to_convert))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
        # Start worker
        self.worker = ConversionWorker(files_to_convert, self.converter)
        self.worker.progress.connect(self._on_progress)
        self.worker.file_done.connect(self._on_file_done)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_progress(self, msg: str):
        self.status_label.setText(msg)
        self.progress_bar.setValue(self.progress_bar.value() + 1)
    
    def _on_file_done(self, filename: str, output_path: str):
        logger.info(f"Extracted: {filename} -> {output_path}")
    
    def _on_finished(self, success: int, total: int):
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("Start Extracting Icons")
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Extracted {success}/{total} icons")
        
        QMessageBox.information(
            self,
            "Extraction Complete",
            f"Successfully extracted {success} of {total} icons.\n\n"
            f"Output location:\n{self.converter.output_dir}\n\n"
            f"Submit these icons to EntropiaNexus.com to help the community!"
        )
    
    def _on_error(self, error_msg: str):
        self.convert_btn.setEnabled(True)
        self.convert_btn.setText("Start Extracting Icons")
        self.progress_bar.setVisible(False)
        self.status_label.setText(f"Error: {error_msg}")
        
        QMessageBox.critical(self, "Error", f"Extraction failed:\n{error_msg}")
    
    def _open_output_folder(self):
        """Open output folder in file manager."""
        import os
        import subprocess
        
        path = str(self.converter.output_dir)
        
        if os.name == 'nt':
            os.startfile(path)
        elif sys.platform == 'darwin':
            subprocess.run(['open', path])
        else:
            subprocess.run(['xdg-open', path])
    
    def closeEvent(self, event):
        """Save settings on close."""
        self._save_settings()
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.worker.wait(1000)
        event.accept()


def set_app_icon(app: QApplication):
    """Set application icon (window icon is set per-window in _load_icon)."""
    # Icon is loaded per-window in IconExtractorWindow._load_icon()
    # This function is kept for compatibility but doesn't need to do anything
    pass


def main():
    """Main entry point."""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application info for proper Windows taskbar icon
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("ImpulsiveFPS")
    
    # Try to set icon
    set_app_icon(app)
    
    # Dark theme with better readability
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #1e1e1e;
        }
        QWidget {
            background-color: #1e1e1e;
            color: #e0e0e0;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #404040;
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 12px;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 8px;
        }
        QPushButton {
            background-color: #3d3d3d;
            border: 1px solid #555;
            padding: 6px 12px;
            border-radius: 4px;
            font-size: 12px;
        }
        QPushButton:hover {
            background-color: #4d4d4d;
        }
        QComboBox {
            background-color: #2d2d2d;
            border: 1px solid #555;
            padding: 5px;
            border-radius: 4px;
        }
        QListWidget {
            background-color: #252525;
            border: 1px solid #404040;
            border-radius: 4px;
        }
        QListWidget::item {
            padding: 6px;
        }
        QListWidget::item:selected {
            background-color: #1565c0;
        }
        QListWidget::item:hover {
            background-color: #2a4d6e;
        }
        QProgressBar {
            border: 1px solid #404040;
            border-radius: 4px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4caf50;
        }
        QTextEdit {
            background-color: #252525;
            border: 1px solid #404040;
        }
        QCheckBox {
            font-size: 12px;
        }
        QLabel {
            font-size: 12px;
        }
    """)
    
    window = IconExtractorWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()