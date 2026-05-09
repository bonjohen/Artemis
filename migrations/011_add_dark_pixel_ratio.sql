-- Add dark_pixel_ratio to feature_image_visual.
-- Fraction of pixels with luminance < 20 (out of 255).
-- Used to exclude nearly-black images from CLIP classification.
ALTER TABLE feature_image_visual ADD COLUMN IF NOT EXISTS dark_pixel_ratio DOUBLE;
