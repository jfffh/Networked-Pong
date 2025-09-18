import struct

BIT_ORDER = "<"

HEADER_FORMAT = "BH"

class binary_message:
    def __init__(self, type:str, encryption_format:str):
        self.type = type
        self.binary_type = ord(self.type)

        self.encryption_format = BIT_ORDER + encryption_format
        self.encryption_format_with_message_header = BIT_ORDER + HEADER_FORMAT + encryption_format

    def encrypt_into_binary(self, *args):
        return struct.pack(self.encryption_format_with_message_header, self.binary_type, struct.calcsize(self.encryption_format), *args)
    
    def decrypt_full_message_from_binary(self, data, offset:int = 0):
        datas = list(struct.unpack_from(self.encryption_format_with_message_header, data, offset))
        datas.pop(0); datas.pop(0)
        if len(datas) == 1:
            return datas[0]
        else:
            return datas
    
    def decrypt_only_message_from_binary(self, data, offset:int = 0):
        return struct.unpack_from(self.encryption_format, data, offset)

class binary_message_handler:
    def __init__(self, message_types:list[binary_message]):
        self.message_types:dict[str:binary_message] = {}
        for message in message_types:
            self.message_types[message.type] = message

    def encrypt_message(self, messages:list[tuple[str, tuple]]):
        encoded_data = []
        for message_type, message_data in messages:
            encoded_data.append(self.message_types[message_type].encrypt_into_binary(*message_data))
        return b"".join(encoded_data)
    
    def decrypt_message(self, data:bytes):
        i = 0

        message_header_length = struct.calcsize(BIT_ORDER + HEADER_FORMAT)
        message_full_length = len(data)

        decrypted_data = []
        decrypted_messages = []
        decrypted_data_length = 0

        while True:
            if len(data) - i < message_header_length:
                break

            message_type, message_length = struct.unpack_from(BIT_ORDER + HEADER_FORMAT, data, i)
            message_type = chr(message_type)

            i += message_header_length
            if i >= message_full_length:
                break

            if message_type in self.message_types:
                if len(data) - i < message_length:
                    break
            
                data = self.message_types[message_type].decrypt_only_message_from_binary(data, i)
                if len(data) == 1:
                    data = data[0]

                decrypted_messages.append(message_type)
                decrypted_data.append(data)
                
                i += message_length
                decrypted_data_length += message_header_length + message_length

                if i >= message_full_length:
                    break
                
        return decrypted_messages, decrypted_data, decrypted_data_length