import csv
import time

class LivePriceSimulator:
    """
    A class to simulate a live data feed from a CSV file.
    """
    def __init__(self, file_path, delay_in_seconds=1):
        """
        Initializes the simulator.
        
        Args:
            file_path (str): The path to the CSV file.
            delay_in_seconds (int/float): The delay between data deliveries.
        """
        self.file_path = file_path
        self.delay = delay_in_seconds
        self.file = None
        self.reader = None
        self.is_finished = False

    def open_file(self):
        """Opens the CSV file and prepares the reader."""
        try:
            self.file = open(self.file_path, 'r', newline='')
            self.reader = csv.reader(self.file)
            next(self.reader) # Skip the header row
        except FileNotFoundError:
            print(f"Error: The file '{self.file_path}' was not found.")
            self.is_finished = True
        except StopIteration:
            print(f"Error: The file '{self.file_path}' is empty.")
            self.is_finished = True

    def get_next_price(self):
        """
        Returns the next price from the data feed.
        
        Returns:
            str: The next price data as a string, or None if the data is exhausted.
        """
        if self.is_finished:
            return None
        
        try:
            # Get the next row from the CSV file
            row = next(self.reader)
            price = row[0]
            
            # Pause to simulate the live data feed
            time.sleep(self.delay)
            
            return price
        except StopIteration:
            print("No more data left. All prices have been delivered.")
            self.is_finished = True
            self.file.close()
            return None

# --- Example Usage ---
if __name__ == "__main__":
    # Create a dummy CSV file for demonstration
    with open('btcusdt.csv', 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['price'])
        writer.writerows([[28500], [28550], [28600], [28590], [28610]])

    # Initialize the simulator with a 1-second delay
    simulator = LivePriceSimulator('btcusdt.csv', delay_in_seconds=1)
    simulator.open_file()
    
    print("Starting data simulation...")
    
    # Loop to get and print the next price until the data is exhausted
    while True:
        price_data = simulator.get_next_price()
        if price_data is None:
            break  # Exit the loop when no more data is available
        print(f"Received new price: {price_data}")