from __future__ import annotations

from typing import Iterable

from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts, sizes


class AgentTheme(Base):
    def __init__(
        self,
        *,
        primary_hue: colors.Color | str = colors.blue,
        secondary_hue: colors.Color | str = colors.slate,
        neutral_hue: colors.Color | str = colors.gray,
        spacing_size: sizes.Size | str = sizes.spacing_md,
        radius_size: sizes.Size | str = sizes.radius_md,
        text_size: sizes.Size | str = sizes.text_lg,
        font: fonts.Font
        | str
        | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("Inter"),
            "ui-sans-serif",
            "system-ui",
            "sans-serif",
        ),
        font_mono: fonts.Font
        | str
        | Iterable[fonts.Font | str] = (
            fonts.GoogleFont("JetBrains Mono"),
            "ui-monospace",
            "Consolas",
            "monospace",
        ),
    ):
        super().__init__(
            primary_hue=primary_hue,
            secondary_hue=secondary_hue,
            neutral_hue=neutral_hue,
            spacing_size=spacing_size,
            radius_size=radius_size,
            text_size=text_size,
            font=font,
            font_mono=font_mono,
        )

        super().set(
            body_background_fill="*neutral_50",
            body_background_fill_dark="*neutral_900",
            block_background_fill="white",
            block_background_fill_dark="*neutral_800",
            block_border_width="1px",
            block_label_background_fill="*primary_50",
            block_label_background_fill_dark="*primary_900",
            block_label_text_color="*primary_500",
            block_label_text_color_dark="*primary_200",
            block_title_text_color="*primary_500",
            block_title_text_color_dark="*primary_200",
            input_background_fill="*neutral_50",
            input_background_fill_dark="*neutral_700",
            button_primary_background_fill="*primary_600",
            button_primary_background_fill_hover="*primary_700",
            button_primary_text_color="white",
            button_secondary_background_fill="*neutral_200",
            button_secondary_background_fill_hover="*neutral_300",
            button_secondary_text_color="*neutral_700",
            button_secondary_text_color_dark="*neutral_200",
        )
