library(tidyverse)
library(ggplot2)
library(exifr)
library(explore)
library(leaflet)

images_path <- '/Users/ashfi/Documents/FUJI Edits'
image_files <- list.files(images_path,  full.names = TRUE)

df <- tibble(read_exif(image_files))

df[sapply(df, is.list)] # we have nested lists in the data

list_cols <- names(df)[sapply(df, is.list)]
print(list_cols)

df[sapply(df, is.list)]


df <- df %>%
    all_of(list_cols)



# Step 2: Check length of each list element per column
lengths_info <- df %>%
  select(all_of(list_cols)) %>%
  mutate(row = row_number()) %>%
  pivot_longer(-row, names_to = "column", values_to = "list_element") %>%
  mutate(length = map_int(list_element, length))

# Step 3: View unusual cases
lengths_info %>%
  group_by(column, length) %>%
  summarise(count = n(), .groups = "drop") %>%
  arrange(desc(count))

Mode <- function(x) {
    ux <- unique(x)
    ux[which.max(tabulate(match(x, ux)))]
  }
  
lengths_info %>%
  group_by(column) %>%
  filter(length != Mode(length))  # Mode is not built-in, see below




# Null coalescing operator
`%||%` <- function(x, y) if (is.null(x)) y else x

clean_list_columns <- function(df, max_extract = 3) {
  list_cols <- names(df)[sapply(df, is.list)]

  for (col in list_cols) {
    col_data <- df[[col]]

    # Determine typical length
    common_len <- Mode(map_int(col_data, length))

    # Try to expand if consistent and small (like GPS or lat/lon)
    if (common_len > 0 && common_len <= max_extract) {
      for (i in seq_len(common_len)) {
        new_col_name <- paste0(col, "_", i)
        df[[new_col_name]] <- map(col_data, ~ .[[i]] %||% NA)
      }
    } else {
      # Otherwise, collapse to string (for inconsistent or large lists)
      df[[paste0(col, "_collapsed")]] <- sapply(col_data, function(x) {
        if (is.null(x)) return(NA_character_)
        if (is.atomic(x)) return(paste(x, collapse = ", "))
        if (is.list(x)) return(paste(unlist(x), collapse = ", "))
        return(as.character(x))
      })
    }

    # Remove original list-column
    df[[col]] <- NULL
  }

  return(df)
}

df_cleaned <- clean_list_columns(df)

drop_na_columns <- function(df, threshold = 0.5) {
    na_props <- colMeans(is.na(df))
    df[, na_props <= threshold]
  }

df_cleaned <- drop_na_columns(df_cleaned)
list_cols <- names(df)[sapply(df_cleaned, is.list)]
print(list_cols)

library(dplyr)
library(tidyr)
library(purrr)
library(rlang)

unnest_list_columns <- function(df, cols_to_unnest, prefix = TRUE) {
  for (col_name in cols_to_unnest) {
    if (!col_name %in% names(df)) next  # skip if column doesn't exist
    
    col_data <- df[[col_name]]
    
    # Skip if not a list
    if (!is.list(col_data)) next

    # Try to unnest to columns
    unnested_df <- tryCatch({
      as_tibble(map_dfr(col_data, ~ as.list(.x)))
    }, error = function(e) {
      message("❌ Skipping ", col_name, " — not unnestable")
      return(NULL)
    })

    if (!is.null(unnested_df)) {
      # Optional: Add prefix to avoid name conflicts
      if (prefix) {
        colnames(unnested_df) <- paste0(col_name, "_", colnames(unnested_df))
      }
      df <- bind_cols(df, unnested_df)
    }

    # Remove the original list-column
    df[[col_name]] <- NULL
  }

  return(df)
}
nested_cols <- c(
    "DateTimeCreated", "DigitalCreationDateTime", "CircleOfConfusion", "FOV", "FocalLength35efl",
    "HyperfocalDistance", "LightValue", "LensID", "LookCluster", "LookParametersRGBTable",
    "LookParametersRGBTableAmount", "MaskGroupBasedCorrectionsCorrectionMasksCorrectionRangeMaskVersion",
    "MaskGroupBasedCorrectionsCorrectionMasksCorrectionRangeMaskType",
    "MaskGroupBasedCorrectionsCorrectionMasksCorrectionRangeMaskColorAmount",
    "MaskGroupBasedCorrectionsCorrectionMasksCorrectionRangeMaskInvert",
    "MaskGroupBasedCorrectionsCorrectionMasksCorrectionRangeMaskSampleType",
    "MaskGroupBasedCorrectionsCorrectionMasksCorrectionRangeMaskPointModels",
    "MaskGroupBasedCorrectionsCorrectionMasksCorrectionRangeMaskLumRange",
    "MaskGroupBasedCorrectionsCorrectionMasksCorrectionRangeMaskLuminanceDepthSampleInfo",
    "RangeMaskMapInfoRangeMaskMapInfoRGBMin", "RangeMaskMapInfoRangeMaskMapInfoRGBMax",
    "RangeMaskMapInfoRangeMaskMapInfoLabMin"
  )
  
df_unnested <- unnest_list_columns(df_cleaned, nested_cols)
  

report(df_unnested, output_dir =  '/Users/ashfi/code/R_projects/photos')

camera_lens <- df_unnested %>%
  filter(!is.na(Lens)) %>%
  count(Lens)


ggplot(camera_lens, aes(x = Lens, y = n)) +
  geom_bar(stat = "identity") +
    scale_x_discrete(labels = c(
        "XF18-55mmF2.8-4 R LM OIS" = "18-55m",
        "XF23mmF2 R WR" = "23mm",
        "XF55-200mmF3.5-4.8 R LM OIS" = "55-200mm", 
        "XF70-300mmF4-5.6 R LM OIS WR" = "70-300mm"
        # Add as many as you want
      )) +
  labs(title = "Lens Usage Frequency",
       x = "Lens",
       y = "Count")

ggplot(df_unnested, aes(FileSize)) + geom_histogram()

library(gganimate)
  # your EXIF tibble
# Filter + convert datetime
df_animate <- df_unnested[!is.na(df_unnested$FocalLength) & !is.na(df_unnested$DateTimeOriginal), ]
df_animate$DateTime <- as.POSIXct(df_animate$DateTimeOriginal, format = "%Y:%m:%d %H:%M:%S")

# (Optional) Extract just the date portion
df_animate$Date <- as.Date(df_animate$DateTime)

# Build animation
p <- ggplot(df_animate, aes(x = FocalLength, fill = LensModel)) +
  geom_histogram(binwidth = 5, color = "white", alpha = 0.8) +
  labs(title = "📸 Focal Lengths Used on {closest_state}",
       x = "Focal Length (mm)",
       y = "Photo Count") +
  theme_minimal() +
  transition_states(Date, transition_length = 2, state_length = 1) +
  enter_fade() +
  exit_shrink()

# Render animation
anim <- animate(p, nframes = 100, fps = 10, width = 800, height = 500)


df_animate$hour <- hour(ymd_hms(df_animate$DateTimeOriginal))

ggplot(df_animate, aes(x = hour)) +
  geom_bar(fill = "purple") +
  labs(title = "Photos by Hour of Day", x = "Hour", y = "Photo Count")

df_animate$ShutterTime <- 2^(-as.numeric(df_animate$ShutterSpeedValue))


ggplot(df_animate, aes(x = ISO, y = ShutterTime, color = as.numeric(FNumber))) +
  geom_point(alpha = 0.6, size = 2) +
  scale_color_gradient(low = "#56B1F7", high = "#132B43") +
  scale_x_log10() +
  scale_y_log10() +
  labs(
    title = "Exposure Triangle: ISO vs Shutter Time",
    x = "ISO (log scale)",
    y = "Shutter Time (s, log scale)",
    color = "F Number"
  ) +
  theme_minimal(base_size = 13) +
  theme(
    panel.grid.minor = element_blank(),
    axis.text.y = element_text(size = 9)
  )

df_animate$ShutterTime <- 2^(-as.numeric(df_animate$ShutterSpeedValue))
df_animate$FNumber <- as.numeric(df_animate$FNumber)
df_animate$Date <- as.Date(ymd_hms(df_animate$DateTimeOriginal))  # or use hour() or ymd_h() for finer scale
  
  shutter_labels <- function(x) {
    label_map <- c("1s", "1/2", "1/4", "1/8", "1/15", "1/30", "1/60", "1/125", "1/250", "1/500", "1/1000", "1/2000", "1/4000")
    pretty_breaks <- c(1, 1/2, 1/4, 1/8, 1/15, 1/30, 1/60, 1/125, 1/250, 1/500, 1/1000, 1/2000, 1/4000)
    label_vec <- setNames(label_map, pretty_breaks)
    label_vec[as.character(x)]
  }
  
  animated_plot <- ggplot(df_animate, aes(x = ISO, y = ShutterTime, color = FNumber)) +
    geom_point(alpha = 0.7, size = 2) +
    scale_color_gradient(low = "#56B1F7", high = "#132B43") +
    scale_x_log10() +
    scale_y_log10(
      breaks = c(1, 1/2, 1/4, 1/8, 1/15, 1/30, 1/60, 1/125, 1/250, 1/500, 1/1000, 1/2000, 1/4000),
      labels = shutter_labels
    ) +
    labs(
      title = "Exposure Triangle Over Time — {closest_state}",
      x = "ISO (log)",
      y = "Shutter Speed (log)",
      color = "F Number"
    ) +
    theme_minimal(base_size = 12) +
    transition_states(Date, transition_length = 2, state_length = 1) +
    ease_aes('cubic-in-out') +
    enter_fade() +
    exit_fade()

animate(animated_plot, fps = 10, duration = 12, width = 800, height = 600, renderer = gifski_renderer("exposure_triangle.gif"))


# Prepare your date column
df_animate$Date <- as.Date(lubridate::ymd_hms(df_animate$DateTimeOriginal))
df_animate$Month <- floor_date(df_animate$Date, unit = "month")

monthly_counts <- df_animate %>%
  count(Month) %>%
  arrange(Month)

p_month <- ggplot(monthly_counts, aes(x = Month, y = n)) +
  geom_line(color = "steelblue", size = 1) +
  geom_point(color = "darkred", size = 2) +
  labs(title = "📆 Monthly Photo Count — {frame_time}",
       x = "Year",
       y = "Photos Taken") +
  theme_minimal(base_size = 14) +
  transition_reveal(Month)

animate(p_month, fps = 10, duration = 8, width = 800, height = 500, renderer = gifski_renderer("monthly_photo_count.gif"))


df_animate$aspect_ratio <- df_animate$ExifImageWidth / df_animate$ExifImageHeight

ggplot(df_animate, aes(x = aspect_ratio)) +
  geom_histogram(binwidth = 0.1, fill = "darkorange") +
  labs(title = "Aspect Ratio Distribution", x = "Aspect Ratio", y = "Count")



exif_df_clean <- df_unnested %>%
  select(where(~ !is.list(.)))

library(corrr)
cor_data <- exif_df_clean %>% 
  drop_na() %>% 
  correlate()

rplot(cor_data)
