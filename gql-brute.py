import requests
import sys
import threading
from colorama import Fore
import re
import json

import argparse
parser = argparse.ArgumentParser(description='Brute force Graph QL endpoints')
parser.add_argument('-w', dest='wordlist', help='Wordlist file', action='store', required=True)
parser.add_argument('-u', dest='url', help='GraphQL URL endpoint', action='store', required=True)
parser.add_argument('-t', dest='threads', help='Threads (default: 10)', action='store', default=10, type=int)
args = parser.parse_args()

objects = []
threads = []
exited = 0

threadLimiter = threading.BoundedSemaphore(args.threads)

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

headers = {'content-type': 'application/json'}

def enum(base):
	with open(args.wordlist) as f:
		for cnt, line in enumerate(f):
			if exited == 0:
				line = base + line.strip()
				threadLimiter.acquire()
				t = threading.Thread(target=test, args=(cnt,line.strip()))
				threads.append(t)
				t.start()

def test(cnt,val,recurse=True):

	# Build query
	pieces = val.split(' / ')
	query = ''
	for piece in pieces:
		query += '{' + piece
	for piece in pieces:
		query += '}'

	# Build path
	path = ' / '.join(pieces[:-1])
	if path != '': path += ' / '

	sys.stdout.write("\033[K")
	sys.stdout.write('\r[%d] %d %s' % (len(pieces),cnt,val))
	sys.stdout.flush()

	data = '{"query":"%s"}' % query
	r = requests.post(args.url, data=data, headers=headers, verify=False)

	# Search for suggestions
	foundObjs = re.findall(r'Did you mean \\"(.*?)\\"\?', r.text)
	if len(foundObjs) > 0 and recurse:
		for foundObj in foundObjs:
			objSplits = foundObj.split('\\" or \\"')
			for objSplit in objSplits:
				objPath = path + objSplit
				if objPath not in objects:
					objects.append(objPath)
					print(Fore.GREEN + "\r\033[K[+] Found: " + objPath + Fore.WHITE)
					try:
						threadLimiter.release()
					except:
						pass

					threadLimiter.acquire()
					t = threading.Thread(target=test, args=(0,objPath,False))
					threads.append(t)
					t.start()

					threadLimiter.acquire()
					newPath = "%s%s" % (objPath, ' / ')
					t = threading.Thread(target=enum, args=(newPath,))
					threads.append(t)
					t.start()

	else:
		parsed = json.loads(r.text)
		if 'data' in parsed:
			print(Fore.MAGENTA + "\r\033[K[+] Data: " + json.dumps(parsed['data']) + Fore.WHITE)
		threadLimiter.release()

try:
	print Fore.BLUE + '[*] Starting' + Fore.WHITE
	enum('')
except KeyboardInterrupt:
	print Fore.YELLOW + '\n[#] Keyboard Interrupt. Exiting...' + Fore.WHITE
	exited = 1
except Exception as e:
	print
	print Fore.RED + e
	raise

# Wait for all threads to finish
for x in threads:
	x.join()

print
print Fore.BLUE + '[.] Done' + Fore.WHITE
