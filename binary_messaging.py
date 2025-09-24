import struct
import math

def repeat(sequence:list):
    new_sequence = []
    for element in sequence:
        new_sequence.append(element)
        new_sequence.append(element)
    return new_sequence

BIT_ORDER = "<"

HEADER_FORMAT = "B"

DELIMITER_FORMAT = "B"
DELIMITER = "\n"

class binary_message:
    def __init__(self, type:str, encryption_format:str):
        self.type = type
        self.binary_type = ord(self.type)

        encryption_format = "".join(repeat(list(encryption_format)))
        header_format = "".join(repeat(list(HEADER_FORMAT)))

        self.encryption_format = BIT_ORDER + encryption_format
        self.encryption_format_with_header_and_delimiter = BIT_ORDER + header_format + encryption_format + DELIMITER_FORMAT
        self.expected_size = struct.calcsize(self.encryption_format)

    def encrypt_into_binary(self, *args):
        return struct.pack(self.encryption_format_with_header_and_delimiter, self.binary_type, self.binary_type, *repeat(args), ord(DELIMITER))
        
    def decrypt_full_message_from_binary(self, data:bytes, offset:int = 0):
        decrypted_data = list(struct.unpack_from(self.encryption_format_with_header_and_delimiter, data, offset))
        
        return_data = []

        for i in range(math.floor(len(decrypted_data) / 2)):
            if decrypted_data[i * 2] != decrypted_data[i * 2 + 1]:
                raise Exception
            return_data.append(decrypted_data[i * 2])

        return_data.pop(0)

        return return_data
        
        
    def decrypt_only_message_from_binary(self, data:bytes, offset:int = 0):
        decrypted_data = struct.unpack_from(self.encryption_format, data, offset)

        return_data = []

        for i in range(math.floor(len(decrypted_data) / 2)):
            if decrypted_data[i * 2] != decrypted_data[i * 2 + 1]:
                raise Exception
            return_data.append(decrypted_data[i * 2])

        return return_data

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

        delimiter = struct.pack(DELIMITER_FORMAT, ord(DELIMITER))

        header = "".join(repeat(HEADER_FORMAT))
        header_size = struct.calcsize(header)
        
        decrypted_data = []
        decrypted_messages = []

        while True:
            delimiter_index = data.find(delimiter, i)

            if delimiter_index == -1:
                return decrypted_messages, decrypted_data, i

            message = data[i:delimiter_index + 1]

            if len(message) < header_size + 1:
                i = delimiter_index + 1
                continue


            header_1, header_2 = struct.unpack_from(header, message, 0)

            if header_1 != header_2:
                i = delimiter_index + 1
                continue

            message_type_type = chr(header_1)

            if not message_type_type in self.message_types:
                i = delimiter_index + 1
                continue

            message_type = self.message_types[chr(header_1)]

            if len(message) <= header_size + message_type.expected_size:
                i = delimiter_index + 1
                continue

            try:   
                message_data = self.message_types[chr(header_1)].decrypt_only_message_from_binary(message, header_size)
                decrypted_messages.append(message_type.type)
                decrypted_data.append(message_data)
            except Exception:
                pass

            i = delimiter_index + 1