# pylint: disable=bad-indentation
try:
	import base64
except ModuleNotFoundError:
	print("Fatal Error Base64 Not Found")		





'''
dictinary for ROT 13  
'''

dict1 = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz123456789'
dict2 = 'NOPQRSTUVWXYZABCDEFGHIJKLMnopqrstuvwxyzabcdefghijklm987654321'
'''
dictinary for morse code  
'''
dict3 = {
        # Letters
        "a": ".-",
        "b": "-...",
        "c": "-.-.",
        "d": "-..",
        "e": ".",
        "f": "..-.",
        "g": "--.",
        "h": "....",
        "i": "..",
        "j": ".---",
        "k": "-.-",
        "l": ".-..",
        "m": "--",
        "n": "-.",
        "o": "---",
        "p": ".--.",
        "q": "--.-",
        "r": ".-.",
        "s": "...",
        "t": "-",
        "u": "..-",
        "v": "...-",
        "w": ".--",
        "x": "-..-",
        "y": "-.--",
        "z": "--..",
        # Numbers
        "0": "-----",
        "1": ".----",
        "2": "..---",
        "3": "...--",
        "4": "....-",
        "5": ".....",
        "6": "-....",
        "7": "--...",
        "8": "---..",
        "9": "----.",
        # Punctuation
        "&": ".-...",
        "'": ".----.",
        "@": ".--.-.",
        ")": "-.--.-",
        "(": "-.--.",
        ":": "---...",
        ",": "--..--",
        "=": "-...-",
        "!": "-.-.--",
        ".": ".-.-.-",
        "-": "-....-",
        "+": ".-.-.",
        '"': ".-..-.",
        "?": "..--..",
        "/": "-..-.",
    }

'''
dictinary for caeser cipher
'''
dict4 = dict(zip("ABCDEFGHIJKLMNOPQRSTUVWXYZ",range(26)))
dict5 = dict(zip(range(26),"ABCDEFGHIJKLMNOPQRSTUVWXYZ"))

  
'''
dictinary for bacon cipher this dict is going to import to easyencryption.py 
'''
dict6 = {'A':'aaaaa', 'B':'aaaab', 'C':'aaaba', 'D':'aaabb', 'E':'aabaa', 
        'F':'aabab', 'G':'aabba', 'H':'aabbb', 'I':'abaaa', 'J':'abaab', 
        'K':'ababa', 'L':'ababb', 'M':'abbaa', 'N':'abbab', 'O':'abbba', 
        'P':'abbbb', 'Q':'baaaa', 'R':'baaab', 'S':'baaba', 'T':'baabb', 
        'U':'babaa', 'V':'babab', 'W':'babba', 'X':'babbb', 'Y':'bbaaa', 'Z':'bbaab'} 

'''
dictinary for a1z26 cipher this dict is going to import to easyencryption.py 
'''
dict7 = {
        # Letters
        "a": "1",
        "b": "2",
        "c": "3",
        "d": "4",
        "e": "5",
        "f": "6",
        "g": "7",
        "h": "8",
        "i": "9",
        "j": "10",
        "k": "11",
        "l": "12",
        "m": "13",
        "n": "14",
        "o": "15",
        "p": "16",
        "q": "17",
        "r": "18",
        "s": "19",
        "t": "20",
        "u": "21",
        "v": "22",
        "w": "23",
        "x": "24",
        "y": "25",
        "z": "26",

        "A": "1",
        "B": "2",
        "C": "3",
        "D": "4",
        "E": "5",
        "F": "6",
        "G": "7",
        "H": "8",
        "I": "9",
        "J": "10",
        "K": "11",
        "L": "12",
        "M": "13",
        "N": "14",
        "O": "15",
        "P": "16",
        "Q": "17",
        "R": "18",
        "S": "19",
        "T": "20",
        "U": "21",
        "V": "22",
        "W": "23",
        "X": "24",
        "Y": "25",
        "Z": "26",
       
    }
  

'''
Data spiritual rebirth have always been widely used utility and one 
among them can be conversion of a string to it’s binary equivalent. 
Let’s discuss certain ways in which this can be done.

encodeion is the strategy by which data is changed over into mystery
code that shrouds the data's actual importance. The study of encoding
and decoding data is called cryptography. In processing, decode1d
information is otherwise called plaintext, and encoded information 
is called ciphertext.
'''
#Keywords

def encode(argv,opti):
	#binary
	if opti == "binary":
		txt_to_bin_converted = ' '.join(format(ord(i), 'b') for i in argv)
		return txt_to_bin_converted

	#flipped
	elif opti == "flipped":
		def process_encode(argv):
			return argv[::-1]
		processedtext = process_encode(argv)
		return processedtext

	#base64
	elif opti == "base64token":
		message_bytes = argv.encode('ascii')
		base64_bytes = base64.b64encode(message_bytes)
		base64_message = base64_bytes.decode('ascii')
		return base64_message


	#ROT13
	elif opti == "rot13conversion":
		def encode(strEnc):
			return strEnc.translate(str.maketrans(dict1, dict2))
		return encode(str(argv))

	elif opti == "morse":
		def encode(argv1): 
			cipher = '' 
			for letter in argv1: 
				if letter != ' ': 
					cipher += dict3[letter] + ' '
				else:
					cipher += ' '
			return cipher
		argv1 = argv
		result = encode(argv1) 
		return result
		
#decodedecodedecodedecodedecodedecodedecodedecodedecodedecodedecodedecode

def decode(argv,opti):

	#binary
	if opti =="binary":
		bin_string = argv
		binary_values = bin_string.split()
		ascii_string = ""
		for binary_value in binary_values:
			integers = int(binary_value, 2)
			ascii_char = chr(integers)
			ascii_string += ascii_char

		return ascii_string

	#flipped
	elif opti == "flipped":
		def process_decode1(arg):
			return arg[::-1]
		processedtextdecode1 = process_decode1(argv)
		return processedtextdecode1

	#base64
	elif opti == "base64token":
		base64_bytes = argv.encode('ascii')
		message_bytes = base64.b64decode(base64_bytes)
		base64_message = message_bytes.decode('ascii')
		return base64_message

	#Morse Code
	elif opti == "morse":
		def decode1(argv1): 
			argv1 += ' '
			decipher = '' 
			citext = '' 
			for letter in argv1: 
				if (letter != ' '): 
					i = 0
					citext += letter
				else:
					i += 1
					if i == 2 :
						decipher += ' '
					else:
						decipher += list(dict3.keys())[list(dict3 .values()).index(citext)]
						citext = ''
			return decipher 

		argv1 = argv
		result = decode1(argv1) 
		return result



