import time

def find_gif_end(data, start_idx):
    try:
        max_len = len(data)
        idx = start_idx + 6 
        if idx + 7 > max_len: return -1
        
        lsd_flags = data[idx + 4]
        idx += 7 
        
        if lsd_flags & 0x80:
            gct_size = 2 ** ((lsd_flags & 0x07) + 1)
            idx += 3 * gct_size
            
        while idx < max_len:
            block_type = data[idx]
            
            if block_type == 0x3B:
                return idx + 1
                
            elif block_type == 0x21:
                idx += 1
                if idx >= max_len: return -1
                idx += 1 
                
                while idx < max_len:
                    length = data[idx]
                    idx += 1
                    if length == 0:
                        break
                    idx += length
                    
            elif block_type == 0x2C:
                idx += 1
                if idx + 9 > max_len: return -1
                id_flags = data[idx + 8]
                idx += 9
                
                if id_flags & 0x80:
                    lct_size = 2 ** ((id_flags & 0x07) + 1)
                    idx += 3 * lct_size
                    
                if idx >= max_len: return -1
                idx += 1 
                
                while idx < max_len:
                    length = data[idx]
                    idx += 1
                    if length == 0:
                        break
                    idx += length
            else:
                return -1
                
            if idx > max_len:
                return -1
                
        return -1
    except IndexError:
        return -1

data = bytearray(64 * 1024 * 1024)
data[0:6] = b'GIF89a'
for i in range(13, len(data)):
    data[i] = 0x21 # Extension block
    
t0 = time.time()
idx = 0
header_idx = data.find(b'GIF89a', idx)
print(f"Header at {header_idx}")
res = find_gif_end(data, header_idx)
print(f"Result: {res}, Time: {time.time() - t0}")
