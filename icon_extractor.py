"""
Entropia Universe Icon Extractor
A standalone tool for extracting game icons from cache.

Usage:
    python icon_extractor.py

Developer: ImpulsiveFPS
Discord: impulsivefps
GitHub: https://github.com/ImpulsiveFPS/EU-Icon-Extractor
"""

import sys
import os
import subprocess
import webbrowser
import re
from pathlib import Path
from typing import Optional, List

# Platform-specific imports
if sys.platform == 'win32':
    import winreg

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QComboBox, QListWidget, QListWidgetItem,
        QFileDialog, QProgressBar, QGroupBox, QMessageBox,
        QTextEdit, QDialog, QScrollArea
    )
    from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSettings
    from PyQt6.QtGui import QIcon, QPixmap, QImage
except ImportError:
    print("PyQt6 not available. Install with: pip install PyQt6")
    sys.exit(1)

try:
    from PIL import Image
except ImportError:
    print("Pillow not available. Install with: pip install Pillow")
    sys.exit(1)


# Application metadata
APP_NAME = "Entropia Universe Icon Extractor"


def get_steam_paths() -> List[Path]:
    """Get all possible Steam installation paths for the current platform."""
    paths = []
    
    if sys.platform == 'win32':
        # Windows: Check registry
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam") as key:
                steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
                paths.append(Path(steam_path))
        except Exception:
            pass
        
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam") as key:
                steam_path, _ = winreg.QueryValueEx(key, "InstallPath")
                paths.append(Path(steam_path))
        except Exception:
            pass
    else:
        # Linux/macOS common Steam paths
        home = Path.home()
        linux_paths = [
            home / ".steam" / "steam",
            home / ".local" / "share" / "Steam",
            home / ".steam" / "root",
        ]
        paths.extend([p for p in linux_paths if p.exists()])
    
    return paths


def parse_library_folders_vdf(vdf_path: Path) -> List[Path]:
    """Parse Steam libraryfolders.vdf to find all library locations."""
    libraries = []
    
    if not vdf_path.exists():
        return libraries
    
    try:
        with open(vdf_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find all "path" entries in the vdf file
        paths = re.findall(r'"path"\s+"([^"]+)"', content)
        
        for path in paths:
            # Replace escaped backslashes (Windows format in VDF)
            path = path.replace('\\\\', '\\')
            libraries.append(Path(path))
    except Exception:
        pass
    
    return libraries


def find_entropia_cache_path() -> Optional[Path]:
    """
    Find Entropia Universe cache folder.
    Checks multiple locations based on platform.
    """
    # Check standard installation first (platform-specific)
    if sys.platform == 'win32':
        standard_paths = [
            Path("C:/ProgramData/Entropia Universe/public_users_data/cache/icon"),
        ]
    else:
        # Linux standard paths
        standard_paths = [
            Path.home() / ".local" / "share" / "Entropia Universe" / "public_users_data" / "cache" / "icon",
        ]
    
    for path in standard_paths:
        if path.exists() and list(path.rglob("*.tga")):
            return path
    
    # Check Steam installations
    steam_paths = get_steam_paths()
    
    for steam_path in steam_paths:
        # Check default Steam library
        eu_path = steam_path / "steamapps" / "common" / "Entropia Universe" / "public_users_data" / "cache" / "icon"
        if eu_path.exists() and list(eu_path.rglob("*.tga")):
            return eu_path
        
        # Check other Steam libraries
        library_folders = steam_path / "steamapps" / "libraryfolders.vdf"
        libraries = parse_library_folders_vdf(library_folders)
        
        for library in libraries:
            eu_path = library / "steamapps" / "common" / "Entropia Universe" / "public_users_data" / "cache" / "icon"
            if eu_path.exists() and list(eu_path.rglob("*.tga")):
                return eu_path
    
    return None


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
    
    CANVAS_SIZE = (320, 320)
    
    def __init__(self, output_dir: Optional[Path] = None):
        if output_dir is None:
            self.output_dir = Path.home() / "Documents" / "Entropia Universe" / "Icons"
        else:
            self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def read_tga_header(self, filepath: Path) -> Optional[TGAHeader]:
        """Read TGA header from file."""
        try:
            with open(filepath, 'rb') as f:
                header_data = f.read(18)
                if len(header_data) < 18:
                    return None
                return TGAHeader(header_data)
        except Exception:
            return None
    
    def load_tga_image(self, filepath: Path) -> Optional[Image.Image]:
        """Load a TGA file as PIL Image."""
        try:
            image = Image.open(filepath)
            if image.mode != 'RGBA':
                image = image.convert('RGBA')
            return image
        except Exception:
            return None
    
    def convert_tga_to_png(self, tga_path: Path, output_name: Optional[str] = None) -> Optional[Path]:
        """Convert a TGA file to PNG with 320x320 canvas."""
        try:
            image = self.load_tga_image(tga_path)
            if not image:
                return None
            
            image = self._apply_canvas(image)
            
            if output_name is None:
                output_name = tga_path.stem
            
            # Ensure output directory exists before saving
            self.output_dir.mkdir(parents=True, exist_ok=True)
            
            output_path = self.output_dir / f"{output_name}.png"
            image.save(output_path, 'PNG')
            
            return output_path
            
        except Exception:
            return None
    
    def _apply_canvas(self, image: Image.Image) -> Image.Image:
        """Place image centered on a 320x320 canvas."""
        canvas_w, canvas_h = self.CANVAS_SIZE
        img_w, img_h = image.size
        
        canvas = Image.new('RGBA', self.CANVAS_SIZE, (0, 0, 0, 0))
        
        x = (canvas_w - img_w) // 2
        y = (canvas_h - img_h) // 2
        
        canvas.paste(image, (x, y), image if image.mode == 'RGBA' else None)
        return canvas


class ConversionWorker(QThread):
    """Background worker for batch conversion."""
    progress = pyqtSignal(str)
    file_done = pyqtSignal(str, str)
    finished = pyqtSignal(int, int)
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
    """Dialog to preview a TGA file at original resolution."""
    
    def __init__(self, tga_path: Path, converter: TGAConverter, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Preview: {tga_path.name}")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        
        info = converter.read_tga_header(tga_path)
        if info:
            info_label = QLabel(f"Original Resolution: {info.width}x{info.height} pixels, {info.pixel_depth}bpp")
            info_label.setStyleSheet("color: #888; font-size: 13px; font-weight: bold;")
            layout.addWidget(info_label)
        
        image = converter.load_tga_image(tga_path)
        if image:
            img_data = image.tobytes("raw", "RGBA")
            qimage = QImage(img_data, image.width, image.height, QImage.Format.Format_RGBA8888)
            pixmap = QPixmap.fromImage(qimage)
            
            img_label = QLabel()
            img_label.setPixmap(pixmap)
            img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_label.setStyleSheet("background-color: #2a2a2a; border: 1px solid #444; padding: 5px;")
            
            scroll = QScrollArea()
            scroll.setWidget(img_label)
            scroll.setWidgetResizable(True)
            scroll.setMinimumSize(min(image.width + 40, 800), min(image.height + 40, 600))
            scroll.setMaximumSize(800, 600)
            layout.addWidget(scroll)
            
            size_label = QLabel(f"Displayed at: {image.width}x{image.height} (Original Size)")
            size_label.setStyleSheet("color: #4caf50; font-size: 12px;")
            size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(size_label)
            
            dialog_width = min(image.width + 50, 820)
            dialog_height = min(image.height + 150, 700)
            self.resize(dialog_width, dialog_height)
        else:
            error_label = QLabel("Failed to load image")
            error_label.setStyleSheet("color: #f44336;")
            layout.addWidget(error_label)
        
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
        
        # Auto-detect cache path
        self.base_cache_path = find_entropia_cache_path()
        self.cache_path_manually_set = False
        
        self.settings = QSettings("ImpulsiveFPS", "EUIconExtractor")
        
        self._setup_ui()
        self._load_icon()
        self._load_settings()
        
        # Detect subfolders if path was found
        if self.base_cache_path:
            self._detect_subfolders()
        else:
            self._show_cache_not_found()
    
    def _show_cache_not_found(self):
        """Show message when cache folder is not found."""
        self.cache_label.setText("❌ Cache folder not found")
        self.cache_label.setStyleSheet(
            "font-family: Consolas; font-size: 10px; color: #f44336; "
            "padding: 6px 8px; background: #3e2723; border-radius: 3px;"
        )
        self.status_label.setText("Click 'Browse...' to select the cache folder manually")
        self.files_count_label.setText("No cache folder selected")
        self.convert_btn.setEnabled(False)
    
    def _browse_cache_folder(self):
        """Browse for cache folder manually."""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Entropia Universe Cache Folder",
            str(Path.home()),
            QFileDialog.Option.ShowDirsOnly
        )
        
        if folder:
            selected_path = Path(folder)
            # Check if this folder or any subfolder contains TGA files
            tga_files = list(selected_path.rglob("*.tga"))
            
            if tga_files:
                self.base_cache_path = selected_path
                self.cache_path_manually_set = True
                self.cache_label.setText(str(selected_path))
                self.cache_label.setStyleSheet(
                    "font-family: Consolas; font-size: 10px; color: #aaa; "
                    "padding: 6px 8px; background: #252525; border-radius: 3px;"
                )
                self.status_label.setText(f"Found {len(tga_files)} TGA files")
                self._detect_subfolders()
            else:
                QMessageBox.warning(
                    self,
                    "No TGA Files Found",
                    f"The selected folder does not contain any .tga files.\n\n"
                    f"Please select the 'cache\\icon' folder from Entropia Universe."
                )
    
    def _setup_ui(self):
        """Setup the UI."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Header
        header_layout = QHBoxLayout()
        header_layout.setSpacing(15)
        
        self.header_icon = QLabel()
        self.header_icon.setFixedSize(48, 48)
        self.header_icon.setStyleSheet("background: transparent;")
        header_layout.addWidget(self.header_icon)
        
        header = QLabel("Entropia Universe Icon Extractor")
        header.setStyleSheet("font-size: 22px; font-weight: bold; color: #4caf50;")
        header_layout.addWidget(header, 1)
        
        self.theme_btn = QPushButton("☀️ Light")
        self.theme_btn.setMaximumWidth(80)
        self.theme_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        self.theme_btn.setCheckable(True)
        self.theme_btn.clicked.connect(self._toggle_theme)
        header_layout.addWidget(self.theme_btn)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # Description
        desc_widget = QWidget()
        desc_layout = QVBoxLayout(desc_widget)
        desc_layout.setContentsMargins(5, 5, 5, 5)
        desc_layout.setSpacing(4)
        
        desc_line1 = QLabel("Extract the item icons from Entropia Universe cache and convert them to PNG.")
        desc_line1.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        desc_layout.addWidget(desc_line1)
        
        desc_line2 = QLabel("You can submit these to ")
        desc_line2.setStyleSheet("color: #aaaaaa; font-size: 13px;")
        
        link_label = QLabel('<a href="https://entropianexus.com" style="color: #4caf50; text-decoration: none;">Entropia Nexus</a> to help complete the item database.')
        link_label.setStyleSheet("font-size: 13px; color: #aaaaaa;")
        link_label.setOpenExternalLinks(True)
        
        desc_line2_layout = QHBoxLayout()
        desc_line2_layout.setContentsMargins(0, 0, 0, 0)
        desc_line2_layout.setSpacing(0)
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
        
        # Display detected or manual path
        if self.base_cache_path:
            path_display = str(self.base_cache_path).replace("/", "\\")
            self.cache_path_full = path_display
        else:
            path_display = "Not found - click Browse to select"
            self.cache_path_full = ""
        
        self.cache_label = QLabel(path_display)
        self.cache_label.setStyleSheet(
            "font-family: Consolas; font-size: 10px; color: #aaa; "
            "padding: 6px 8px; background: #252525; border-radius: 3px;"
        )
        self.cache_label.setWordWrap(True)
        cache_layout.addWidget(self.cache_label)
        
        # Subfolder selector and browse button
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
        
        # Browse button for manual selection
        browse_btn = QPushButton("📂 Browse...")
        browse_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        browse_btn.clicked.connect(self._browse_cache_folder)
        cache_layout.addWidget(browse_btn)
        
        top_row_layout.addWidget(cache_group, 1)
        
        # Output folder
        output_group = QGroupBox("💾 Output Location")
        output_group.setStyleSheet("QGroupBox { font-size: 13px; font-weight: bold; }")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(12, 18, 12, 12)
        output_layout.setSpacing(10)
        
        output_info = QLabel("📁 Icons saved to your Documents folder (same location as chat.log)")
        output_info.setStyleSheet("color: #666666; font-size: 12px;")
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
        
        # Available Icons
        files_group = QGroupBox("📄 Available Icons")
        files_group.setStyleSheet("QGroupBox { font-size: 13px; font-weight: bold; }")
        files_layout = QVBoxLayout(files_group)
        files_layout.setContentsMargins(12, 18, 12, 12)
        files_layout.setSpacing(10)
        
        files_info = QLabel("💡 Double-click an icon to preview. Select icons to extract (or leave blank for all).")
        files_info.setStyleSheet("color: #666666; font-size: 12px;")
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
        
        # Bottom buttons
        bottom_widget = QWidget()
        bottom_layout = QHBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(15)
        
        select_layout = QHBoxLayout()
        select_layout.setSpacing(10)
        
        select_all_btn = QPushButton("☑️ Select All")
        select_all_btn.setMaximumWidth(100)
        select_all_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        select_all_btn.clicked.connect(self.files_list.selectAll)
        select_layout.addWidget(select_all_btn)
        
        select_none_btn = QPushButton("⬜ Select None")
        select_none_btn.setMaximumWidth(100)
        select_none_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        select_none_btn.clicked.connect(self.files_list.clearSelection)
        select_layout.addWidget(select_none_btn)
        
        bottom_layout.addLayout(select_layout)
        bottom_layout.addStretch()
        
        right_buttons = QVBoxLayout()
        right_buttons.setSpacing(8)
        right_buttons.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.convert_btn = QPushButton("▶️ Start Extracting Icons")
        self.convert_btn.setFixedSize(200, 45)
        self.convert_btn.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                font-weight: bold;
                font-size: 13px;
                border-radius: 5px;
                padding: 10px;
                color: white;
            }
            QPushButton:hover { background-color: #66bb6a; }
            QPushButton:disabled { background-color: #757575; color: #bdbdbd; }
        """)
        self.convert_btn.clicked.connect(self._start_conversion)
        right_buttons.addWidget(self.convert_btn)
        
        open_folder_btn = QPushButton("📂 Open Output Folder")
        open_folder_btn.setFixedSize(200, 35)
        open_folder_btn.setStyleSheet("font-size: 11px; padding: 5px;")
        open_folder_btn.clicked.connect(self._open_output_folder)
        right_buttons.addWidget(open_folder_btn)
        
        bottom_layout.addLayout(right_buttons)
        
        layout.addWidget(bottom_widget)
        
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
        
        # Important Information
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
        
        # Footer
        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(10, 10, 10, 10)
        footer_layout.setSpacing(5)
        
        footer_line1 = QLabel('Developed by ImpulsiveFPS | <a href="https://github.com/ImpulsiveFPS/EU-Icon-Extractor" style="color: #888;">GitHub</a> | <a href="https://github.com/ImpulsiveFPS/EU-Icon-Extractor/issues" style="color: #ff9800;">Report Bug</a> | <a href="https://ko-fi.com/impulsivefps" style="color: #ff6b6b;">Support me on Ko-fi</a>')
        footer_line1.setStyleSheet("color: #888; font-size: 11px;")
        footer_line1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer_line1.setOpenExternalLinks(True)
        footer_layout.addWidget(footer_line1)
        
        # Star on GitHub line
        star_label = QLabel('If you like this app, please <a href="https://github.com/ImpulsiveFPS/EU-Icon-Extractor" style="color: #ffd700;">give it a star on GitHub</a>!')
        star_label.setStyleSheet("color: #888; font-size: 11px;")
        star_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        star_label.setOpenExternalLinks(True)
        footer_layout.addWidget(star_label)
        
        disclaimer_widget = QWidget()
        disclaimer_layout = QHBoxLayout(disclaimer_widget)
        disclaimer_layout.setContentsMargins(0, 0, 0, 0)
        disclaimer_layout.setSpacing(0)
        
        label1 = QLabel("Entropia Universe Icon Extractor is a fan-made resource and is not affiliated with ")
        label1.setStyleSheet("color: #666; font-size: 10px;")
        
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
            dialog = PreviewDialog(filepath, self.converter, self)
            dialog.exec()
    
    def _load_icon(self):
        """Load and set the application icon."""
        icon_path = Path(__file__).parent / "icon.ico"
        if not icon_path.exists():
            icon_path = Path(__file__).parent / "assets" / "icon.ico"
        
        if icon_path.exists():
            pixmap = QPixmap(str(icon_path))
            if not pixmap.isNull():
                self.setWindowIcon(QIcon(pixmap))
                header_pixmap = pixmap.scaled(48, 48, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
                self.header_icon.setPixmap(header_pixmap)
                return True
        
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
                color: #333333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #333333;
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
                background-color: #2d2818;
                border: 1px solid #5d4e37;
                color: #ffc107;
            }
            QLabel {
                font-size: 12px;
                color: #333333;
            }
        """)
    
    def _load_settings(self):
        """Load saved settings."""
        saved_output = self.settings.value("output_dir", str(self.converter.output_dir))
        self.converter.output_dir = Path(saved_output)
        self.output_label.setText("Documents\\Entropia Universe\\Icons\\")
    
    def _save_settings(self):
        """Save current settings."""
        self.settings.setValue("output_dir", str(self.converter.output_dir))
    
    def _detect_subfolders(self):
        """Detect version subfolders in the cache directory."""
        self.subfolder_combo.clear()
        
        if not self.base_cache_path or not self.base_cache_path.exists():
            self.cache_label.setText("❌ Cache folder not found")
            self.cache_label.setStyleSheet(
                "font-family: Consolas; font-size: 10px; color: #f44336; "
                "padding: 6px 8px; background: #3e2723; border-radius: 3px;"
            )
            self.status_label.setText("Click 'Browse...' to select the cache folder manually")
            self.files_count_label.setText("No cache folder selected")
            self.convert_btn.setEnabled(False)
            return
        
        subfolders = []
        for item in self.base_cache_path.iterdir():
            if item.is_dir():
                tga_count = len(list(item.glob("*.tga")))
                if tga_count > 0:
                    subfolders.append((item.name, tga_count, item))
        
        if not subfolders:
            self.cache_label.setText(f"No subfolders with icons in {self.base_cache_path}")
            self.status_label.setText("No version folders found")
            return
        
        subfolders.sort(key=lambda x: x[0])
        
        for name, count, path in subfolders:
            self.subfolder_combo.addItem(f"{name} ({count} icons)", str(path))
        
        total_icons = sum(s[1] for s in subfolders)
        self.subfolder_combo.insertItem(0, f"All Folders ({total_icons} icons)", "all")
        self.subfolder_combo.setCurrentIndex(0)
        
        # Update display
        display_path = str(self.base_cache_path).replace("/", "\\")
        self.cache_label.setText(display_path)
        self.cache_label.setStyleSheet(
            "font-family: Consolas; font-size: 10px; color: #aaa; "
            "padding: 6px 8px; background: #252525; border-radius: 3px;"
        )
        self.status_label.setText(f"Found {len(subfolders)} version folders")
        
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
            self.output_label.setText("Documents\\Entropia Universe\\Icons\\")
            self._save_settings()
    
    def _refresh_file_list(self):
        """Refresh the list of found files based on current selection."""
        self.files_list.clear()
        self.found_files = []
        
        if not self.base_cache_path or not self.base_cache_path.exists():
            return
        
        path_data = self.subfolder_combo.currentData()
        if path_data == "all" or path_data is None:
            folders_to_scan = [d for d in self.base_cache_path.iterdir() if d.is_dir()]
        else:
            folders_to_scan = [Path(path_data)]
        
        tga_files = []
        for folder in folders_to_scan:
            if folder.exists():
                tga_files.extend(folder.glob("*.tga"))
        
        self.files_count_label.setText(f"Found {len(tga_files)} icon files")
        self.status_label.setText(f"Found {len(tga_files)} files")
        
        for tga_file in sorted(tga_files):
            try:
                rel_path = f"{tga_file.parent.name}/{tga_file.name}"
            except:
                rel_path = tga_file.name
            
            item = QListWidgetItem(rel_path)
            item.setData(Qt.ItemDataRole.UserRole, str(tga_file))
            
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
        
        self._save_settings()
        
        self.convert_btn.setEnabled(False)
        self.convert_btn.setText("Extracting...")
        self.progress_bar.setRange(0, len(files_to_convert))
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        
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
        pass
    
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
    """Set application icon for window and taskbar."""
    icon_path = Path(__file__).parent / "icon.ico"
    if not icon_path.exists():
        icon_path = Path(__file__).parent / "assets" / "icon.ico"
    
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
        return True
    return False


def set_windows_taskbar_icon():
    """Set Windows taskbar icon properly."""
    if sys.platform == 'win32':
        try:
            import ctypes
            myappid = 'impulsivefps.euiconextractor.1.0'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass


def main():
    """Main entry point."""
    set_windows_taskbar_icon()
    
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ImpulsiveFPS")
    
    set_app_icon(app)
    
    # Dark theme by default
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
        QLabel {
            font-size: 12px;
        }
    """)
    
    window = IconExtractorWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
