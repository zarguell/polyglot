import { readFileSync } from "fs";
import { resolve } from "path";

interface DesignTokens {
  app_name: string;
  tagline: string;
  appearance: {
    primary_color: string;
    primary_hover: string;
    surface: string;
    surface_secondary: string;
    border: string;
    text: string;
    text_secondary: string;
    font_family: string;
    border_radius: string;
    density: string;
    dark_mode_supported: boolean;
  };
}

const tokensPath = resolve(__dirname, "..", "DESIGN_TOKENS.json");
const tokens: DesignTokens = JSON.parse(readFileSync(tokensPath, "utf-8"));
const a = tokens.appearance;

const config = {
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: a.primary_color,
          hover: a.primary_hover,
        },
        surface: {
          DEFAULT: a.surface,
          secondary: a.surface_secondary,
        },
        border: a.border,
        text: {
          DEFAULT: a.text,
          secondary: a.text_secondary,
        },
      },
      fontFamily: {
        sans: [a.font_family],
      },
      borderRadius: {
        lg: a.border_radius,
      },
    },
  },
};

export default config;
