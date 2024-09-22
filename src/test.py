import sys
import time

for i in range(100, 0, -1):
    print(f'\x1b[2K\r{i:,} inserted.', end='\r')
    sys.stdout.flush()
    time.sleep(0.1)  # 100 milliseconds delay
print(f'Done.')
sys.stdout.flush()
