import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import label, center_of_mass

# Load CSV data
def load_csv(file_path):
    with open(file_path, 'r') as file:
        data = file.readlines()
    frames = []
    for i in range(0, len(data), 2):  # Frame numbers on odd rows, data on even rows
        frame_data = np.array([float(x) for x in data[i+1].strip().split(',')])
        frames.append(frame_data.reshape(8, 8))
    return frames

# Extract blob and calculate central mass
def calculate_largest_blob_and_central_mass(grid, top_percentile=95):
    highest_temp = np.percentile(grid, top_percentile)  # Top percentile for "person"
    blob_mask = grid >= highest_temp                   # Mask for "person" blob
    labeled_array, num_features = label(blob_mask)     # Label contiguous blobs
    
    # Find the largest blob by pixel count
    largest_blob_idx = None
    largest_blob_size = 0
    for i in range(1, num_features + 1):
        blob_size = np.sum(labeled_array == i)
        if blob_size > largest_blob_size:
            largest_blob_size = blob_size
            largest_blob_idx = i
    
    # Calculate the central mass of the largest blob
    if largest_blob_idx is not None:
        center = center_of_mass(blob_mask, labeled_array, [largest_blob_idx])[0]
        return [center]  # Return the central mass as a list
    else:
        return []  # No blobs found

# Plotting the central mass movement
def plot_central_mass(frames, pause_time=0.3):   #0.2
    fig, ax = plt.subplots()
    
    # Set a consistent color range for all frames
    vmin = np.min([np.min(frame) for frame in frames])  # Global min temperature
    vmax = np.max([np.max(frame) for frame in frames])  # Global max temperature
    
    for i, frame in enumerate(frames):
        ax.clear()
        # Calculate the largest blob and its central mass
        blob_centers = calculate_largest_blob_and_central_mass(frame)
        
        # Display grid and central mass points
        heatmap = ax.imshow(frame, cmap='coolwarm', interpolation='nearest', vmin=vmin, vmax=vmax)
        for center in blob_centers:
            ax.plot(center[1], center[0], 'ro', label="Central Mass" if i == 0 else "")
        ax.set_title(f'Frame {i + 1}')
        ax.legend()
        
        # Add color bar for better visualization
        if i == 0:
            plt.colorbar(heatmap, ax=ax, orientation='vertical', label="Temperature (°C)")
        
        plt.pause(pause_time)
    plt.show()

# Main Execution
file_path = "SittingUpandFallingTowardsTail.csv"  # Replace with your actual CSV file path
frames = load_csv(file_path)
plot_central_mass(frames)
