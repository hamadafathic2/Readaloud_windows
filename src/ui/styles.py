"""Windows 11 Fluent design system, theme tokens, and embedded vector SVGs."""

COLORS = {
    # Backgrounds
    "bg_dark": "rgba(20, 24, 33, 0.94)",
    "bg_dark_solid": "#141821",
    "bg_surface": "#1e2433",
    "bg_surface_hover": "#2b3447",
    "bg_card": "#232a3b",
    
    # Accents & Brand
    "accent_primary": "#3b82f6",      # Windows 11 Electric Blue
    "accent_secondary": "#8b5cf6",    # Electric Violet
    "accent_gradient_start": "#2563eb",
    "accent_gradient_end": "#7c3aed",
    "accent_glow": "rgba(99, 102, 241, 0.45)",
    
    # States
    "state_playing": "#10b981",       # Emerald Green
    "state_playing_glow": "rgba(16, 185, 129, 0.5)",
    "state_paused": "#f59e0b",        # Amber
    "state_error": "#ef4444",         # Rose Red
    
    # Typography & Borders
    "text_primary": "#f8fafc",
    "text_secondary": "#94a3b8",
    "text_muted": "#64748b",
    "border_subtle": "rgba(255, 255, 255, 0.12)",
    "border_focus": "rgba(96, 165, 250, 0.8)",
}

DIALOG_STYLE = f"""
QDialog {{
    background-color: {COLORS['bg_dark_solid']};
    color: {COLORS['text_primary']};
    font-family: 'Segoe UI Variable Display', 'Segoe UI', 'Inter', sans-serif;
    font-size: 13px;
}}

QLabel {{
    color: {COLORS['text_primary']};
    font-size: 13px;
}}

QLabel#titleLabel {{
    font-size: 18px;
    font-weight: 700;
    color: #ffffff;
}}

QLabel#sectionTitle {{
    font-size: 14px;
    font-weight: 600;
    color: {COLORS['accent_primary']};
    padding-top: 8px;
}}

QGroupBox {{
    background-color: {COLORS['bg_surface']};
    border: 1px solid {COLORS['border_subtle']};
    border-radius: 8px;
    margin-top: 16px;
    padding-top: 14px;
    font-weight: 600;
    color: {COLORS['text_secondary']};
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 0 6px;
}}

QComboBox {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_subtle']};
    border-radius: 6px;
    padding: 6px 12px;
    font-size: 13px;
    min-height: 36px;
}}

QComboBox:hover {{
    border-color: {COLORS['accent_primary']};
}}

QComboBox::drop-down {{
    border: none;
    width: 28px;
}}

QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_surface']};
    color: {COLORS['text_primary']};
    selection-background-color: {COLORS['accent_primary']};
    border: 1px solid {COLORS['border_subtle']};
    outline: none;
    padding: 4px;
}}

QSlider::groove:horizontal {{
    height: 6px;
    background: {COLORS['bg_card']};
    border-radius: 3px;
}}

QSlider::sub-page:horizontal {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['accent_gradient_start']}, stop:1 {COLORS['accent_gradient_end']});
    border-radius: 3px;
}}

QSlider::handle:horizontal {{
    background: #ffffff;
    border: 2px solid {COLORS['accent_primary']};
    width: 16px;
    margin-top: -5px;
    margin-bottom: -5px;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: {COLORS['accent_primary']};
    border-color: #ffffff;
}}

QPushButton {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_subtle']};
    border-radius: 6px;
    padding: 6px 16px;
    font-weight: 600;
    font-size: 13px;
    min-height: 34px;
}}


QPushButton:hover {{
    background-color: {COLORS['bg_surface_hover']};
    border-color: {COLORS['accent_primary']};
}}

QPushButton:pressed {{
    background-color: {COLORS['accent_primary']};
    color: #ffffff;
}}

QPushButton#primaryBtn {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 {COLORS['accent_gradient_start']}, stop:1 {COLORS['accent_gradient_end']});
    border: none;
    color: #ffffff;
}}

QPushButton#primaryBtn:hover {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3b82f6, stop:1 #8b5cf6);
}}

QCheckBox {{
    color: {COLORS['text_primary']};
    spacing: 8px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid {COLORS['border_subtle']};
    background-color: {COLORS['bg_card']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['accent_primary']};
    border-color: {COLORS['accent_primary']};
}}

QLineEdit {{
    background-color: {COLORS['bg_card']};
    color: {COLORS['text_primary']};
    border: 1px solid {COLORS['border_subtle']};
    border-radius: 6px;
    padding: 6px 10px;
}}

QLineEdit:focus {{
    border-color: {COLORS['border_focus']};
}}
"""

# Embedded clean modern SVG graphics
SVG_ICONS = {
    "play": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="5 3 19 12 5 21 5 3" fill="currentColor"/>
    </svg>""",
    "pause": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round">
        <line x1="7" y1="4" x2="7" y2="20" stroke="currentColor"/>
        <line x1="17" y1="4" x2="17" y2="20" stroke="currentColor"/>
    </svg>""",
    "stop": """<svg viewBox="0 0 24 24" fill="currentColor">
        <rect x="5" y="5" width="14" height="14" rx="2" fill="currentColor"/>
    </svg>""",
    "snip": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="6" cy="6" r="3"/>
        <circle cx="6" cy="18" r="3"/>
        <line x1="20" y1="4" x2="8.12" y2="15.88"/>
        <line x1="14.47" y1="14.48" x2="20" y2="20"/>
        <line x1="8.12" y1="8.12" x2="12" y2="12"/>
    </svg>""",
    "speed": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2" fill="currentColor"/>
    </svg>""",
    "voice": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 1a3 3 0 0 0-3 3v8a3 3 0 0 0 6 0V4a3 3 0 0 0-3-3z"/>
        <path d="M19 10v2a7 7 0 0 1-14 0v-2"/>
        <line x1="12" y1="19" x2="12" y2="23"/>
        <line x1="8" y1="23" x2="16" y2="23"/>
    </svg>""",
    "settings": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <circle cx="12" cy="12" r="3"/>
        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
    </svg>""",
    "speaker": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
        <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" fill="currentColor"/>
        <path d="M15.54 8.46a5 5 0 0 1 0 7.07"/>
        <path d="M19.07 4.93a10 10 0 0 1 0 14.14"/>
    </svg>""",
    "close": """<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <line x1="18" y1="6" x2="6" y2="18"/>
        <line x1="6" y1="6" x2="18" y2="18"/>
    </svg>""",
}
