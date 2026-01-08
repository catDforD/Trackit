"""
Font configuration for Chinese characters in visualizations.

This module provides utilities for configuring Matplotlib to properly
display Chinese characters in plots and charts.

Author: Trackit Development
"""

import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import platform
import os
from typing import Optional, List


class FontConfig:
    """
    Configure fonts for Chinese character display in Matplotlib.

    This class handles font detection and configuration to ensure
    Chinese characters display correctly in visualizations.

    Example:
        >>> FontConfig.setup_chinese_font()
        >>> plt.title("中文标题")
        >>> plt.show()
    """

    # Common Chinese fonts by platform
    FONTS_BY_PLATFORM = {
        'Linux': [
            'WenQuanYi Micro Hei',
            'WenQuanYi Zen Hei',
            'Noto Sans CJK SC',
            'Droid Sans Fallback',
            'SimHei',
            'DejaVu Sans',
        ],
        'Darwin': {  # macOS
            'PingFang SC',
            'Heiti SC',
            'STHeiti',
            'Hiragino Sans GB',
            'Microsoft YaHei',
        },
        'Windows': {
            'Microsoft YaHei',
            'SimHei',
            'SimSun',
            'KaiTi',
            'FangSong',
        }
    }

    # Fallback fonts (try these if platform-specific fonts fail)
    FALLBACK_FONTS = [
        'Arial Unicode MS',
        'Segoe UI Symbol',
        'DejaVu Sans',
    ]

    @staticmethod
    def get_available_fonts() -> List[str]:
        """
        Get list of available Chinese fonts on the system.

        Returns:
            List of available font names
        """
        system = platform.system()
        font_candidates = FontConfig.FONTS_BY_PLATFORM.get(system, FontConfig.FALLBACK_FONTS)

        # Get all available fonts
        available_fonts = [f.name for f in fm.fontManager.ttflist]

        # Find matching fonts
        found_fonts = []
        for candidate in font_candidates:
            if candidate in available_fonts:
                found_fonts.append(candidate)

        return found_fonts

    @staticmethod
    def setup_chinese_font(font_name: Optional[str] = None) -> bool:
        """
        Setup matplotlib to use Chinese font.

        Args:
            font_name: Specific font name to use (optional, auto-detect if None)

        Returns:
            True if setup successful, False otherwise
        """
        try:
            # Get available fonts
            if font_name is None:
                available_fonts = FontConfig.get_available_fonts()
                if not available_fonts:
                    print("Warning: No Chinese fonts found, using system default")
                    return False
                font_name = available_fonts[0]

            # Configure matplotlib
            plt.rcParams['font.sans-serif'] = [font_name, 'DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False  # Fix minus sign display

            print(f"✓ Chinese font configured: {font_name}")
            return True

        except Exception as e:
            print(f"Warning: Could not configure Chinese font: {e}")
            # Fallback to default
            plt.rcParams['font.sans-serif'] = ['DejaVu Sans']
            plt.rcParams['axes.unicode_minus'] = False
            return False

    @staticmethod
    def test_font_display() -> None:
        """Test if Chinese characters display correctly."""
        FontConfig.setup_chinese_font()

        import matplotlib.pyplot as plt
        import numpy as np

        # Create test plot
        x = np.linspace(0, 10, 100)
        y = np.sin(x)

        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(x, y)
        ax.set_title('中文字体测试 - Font Test')
        ax.set_xlabel('横轴标签 (X-axis)')
        ax.set_ylabel('纵轴标签 (Y-axis)')
        ax.grid(True, alpha=0.3)

        # Add legend
        ax.legend(['正弦波'], loc='upper right')

        plt.tight_layout()
        plt.savefig('/tmp/font_test.png', dpi=100, bbox_inches='tight')
        print("✓ Font test saved to /tmp/font_test.png")
        plt.close()

    @staticmethod
    def get_font_info() -> dict:
        """
        Get information about current font configuration.

        Returns:
            Dictionary with font information
        """
        return {
            'platform': platform.system(),
            'available_chinese_fonts': FontConfig.get_available_fonts(),
            'current_font': plt.rcParams.get('font.sans-serif', ['DejaVu Sans'])[0],
            'matplotlib_version': plt.__version__,
        }


# Auto-setup on module import
def setup_auto():
    """Automatically setup Chinese font configuration."""
    FontConfig.setup_chinese_font()


# Setup automatically when module is imported
setup_auto()


if __name__ == "__main__":
    print("Font Configuration Test")
    print("=" * 60)

    # Get font info
    info = FontConfig.get_font_info()
    print(f"\nPlatform: {info['platform']}")
    print(f"Matplotlib version: {info['matplotlib_version']}")
    print(f"Current font: {info['current_font']}")
    print(f"Available Chinese fonts: {info['available_chinese_fonts']}")

    # Test font display
    print("\nTesting font display...")
    FontConfig.test_font_display()

    print("\n✓ Font configuration complete!")
