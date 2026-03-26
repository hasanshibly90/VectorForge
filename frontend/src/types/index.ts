export interface User {
  id: string;
  email: string;
  is_active: boolean;
  created_at: string;
}

export interface ApiKey {
  id: string;
  key_prefix: string;
  name: string | null;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
  raw_key?: string;
}

export interface ConversionSettings {
  colormode: "color" | "binary";
  detail_level: number;
  smoothing: number;
  output_formats: string[];
}

export interface LayerInfo {
  name: string;
  color_hex: string;
  area_pct: number;
  svg_file: string;
}

export interface ConversionOutputs {
  combined_svg?: string;
  bmp?: string;
  png?: string;
  layers_json?: string;
  viewer?: string;
  layer_svgs?: string[];
}

export interface Conversion {
  id: string;
  status: "pending" | "processing" | "completed" | "failed";
  original_filename: string;
  original_format: string;
  original_size_bytes: number;
  settings: ConversionSettings;
  share_token: string | null;
  share_url: string | null;
  processing_time_ms: number | null;
  error_message: string | null;
  engine_used: string | null;
  layers: LayerInfo[];
  outputs: ConversionOutputs;
  created_at: string;
  completed_at: string | null;
}

export interface ConversionList {
  conversions: Conversion[];
  total: number;
  page: number;
  per_page: number;
}

export interface BatchResponse {
  batch_id: string;
  conversions: Conversion[];
  total: number;
}

export interface UsageData {
  period_start: string;
  period_end: string;
  total_conversions: number;
  successful_conversions: number;
  failed_conversions: number;
}

export interface Webhook {
  id: string;
  url: string;
  events: string[];
  is_active: boolean;
  created_at: string;
}
