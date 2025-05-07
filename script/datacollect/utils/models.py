import seaborn as sns

def get_model_visualization_scheme(models=None):
    
    # Get the deep color palette for better contrast
    #deep_palette = sns.color_palette("deep", 12)  # Get enough colors for all models
    deep_palette = sns.color_palette("tab10", 12)  # Original color palette    
    
    # Convert RGB tuples to hex for easier use
    deep_palette_hex = []
    for rgb in deep_palette:
        hex_color = '#%02x%02x%02x' % (int(rgb[0]*255), int(rgb[1]*255), int(rgb[2]*255))
        deep_palette_hex.append(hex_color)
    
    # Fixed mapping of models to colors from deep palette and markers
    model_scheme = {
        "Llama3-70B":       {"color": deep_palette_hex[0], "marker": "s"},  # Blue with plus
        "Llama3-8B":        {"color": deep_palette_hex[1], "marker": "o"},  # Orange with circle
        "Llama3.3-70B":     {"color": deep_palette_hex[2], "marker": "D"},  # Green with diamond
        "Gemini-1.5-Flash": {"color": deep_palette_hex[3], "marker": "x"},  # Red with square
        "GPT-4o-Mini":      {"color": deep_palette_hex[4], "marker": "^"},  # Purple with triangle up
        "GPT-4.1-Mini":     {"color": deep_palette_hex[5], "marker": "*"},  # Brown
        "Mixtral-8x7B":     {"color": deep_palette_hex[6], "marker": "v"},  #  with triangle down
    }
    
    # If specific models requested, filter the mapping
    if models is not None:
        filtered_scheme = {}
        for i, model in enumerate(models):
            if model in model_scheme:
                filtered_scheme[model] = model_scheme[model]
            else:
                # For unknown models, assign the next color in the palette
                # and cycle through markers
                markers = ['+', 'o', 'D', 's', '^', 'v', 'x', '*', 'p', 'h', '8', '.']
                color_idx = i % len(deep_palette_hex)
                marker_idx = i % len(markers)
                filtered_scheme[model] = {
                    "color": deep_palette_hex[color_idx], 
                    "marker": markers[marker_idx]
                }
        return filtered_scheme
    
    # Otherwise return complete mapping
    return model_scheme

# Utility function to get colors and markers as separate lists
def get_colors_and_markers(models):
    scheme = get_model_visualization_scheme(models)
    colors = [scheme[model]["color"] for model in models]
    markers = [scheme[model]["marker"] for model in models]
    return colors, markers
