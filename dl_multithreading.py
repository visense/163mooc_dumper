#HTTP大文件多线程下载，支持断点续传

from ThreadPool import *
from time import sleep
import os
import urllib.request as urllib

def _len(url):
	req = urllib.Request(url)
	req.get_method = lambda:'HEAD'
	length = urllib.urlopen(req).info().get('Content-Length')
	if length: return int(length)

def _download_bf(url, bfs, i, tmp):
	bf = bfs[i][1]
	req = urllib.Request(url)
	req.add_header('Range', bf)
	tmp_path = os.path.join(tmp, '%s.tmp' % i)
	if os.path.isfile(tmp_path):
		fsize = os.path.getsize(tmp_path)
		range_size = bf.split('bytes=')[-1].split('-')
		range_size = int(range_size[1]) - int(range_size[0]) + 1
		if fsize == range_size:
			result = (True, tmp_path)
			bfs[i] = result
			return
		else:
			os.unlink(tmp_path)
	try:
		res = urllib.urlopen(req)
		with open(tmp_path, 'wb') as f:
			f.write(res.read())
	except:
		if os.path.isfile(tmp_path): os.unlink(tmp_path)
		_download_bf(url, bfs, i, tmp)
		return
	result = (True, tmp_path)
	bfs[i] = result

def _merge(bfs, fn, tmp):
	with open(fn, 'wb') as f:
		for bf_path in map(lambda x:x[1], bfs):
			with open(bf_path, 'rb') as bf:
				f.write(bf.read())
			os.unlink(bf_path)
	os.rmdir(tmp)

def _count(bfs, bfsz, length, end):
	count = list(map(lambda x:int(x[0]), bfs))
	end_done = count[-1]
	count = sum(count)
	if count == len(bfs):
		return 'done'
	count *= bfsz
	if end_done:
		count = count - bfsz + end
	percent = count * 1000 // length / 10
	count = count / 1024 / 1024 * 10 // 1 / 10
	length = length / 1024 / 1024 * 10 // 1 / 10
	return (str(percent) + '%', '%sMB' % count, '%sMB' % length)

def download(url, fn, threads=30, bfsz=1048576, sep=0.2):
	name = fn.split(os.path.sep)[-1]
	tmp = os.path.join('.', 'tmp_%s' % name)
	if not os.path.isdir(tmp): os.makedirs(tmp)
	length = _len(url)
	_length = length / 1
	end = None
	at = 0
	bfs = []
	while length > 0:
		if length > bfsz:
			bf = 'bytes=%s-%s' % (at, at + bfsz - 1)
		else:
			bf = 'bytes=%s-%s' % (at, at + length - 1)
			end = length
		bfs.append((False, bf))
		at += bfsz
		length -= bfsz
	with Pool(threads) as pool:
		for i in range(len(bfs)):
			pool.add(_download_bf, (url, bfs, i, tmp))
	while True:
		status = _count(bfs, bfsz, _length, end)
		if status == 'done':
			yield 'Merging...'
			break
		yield status
		sleep(sep)
	_merge(bfs, fn, tmp)
	yield 'done'

if __name__ == '__main__':
	url = 'http://mov.bn.netease.com/open-movie/nos/mp4/2014/08/22/SA3B20K2U_sd.mp4'
	fn = 'test.mp4'
	d = download(url, fn)
	for i in d:
		if type(i) == tuple:
			print('%s %s/%s' % i)
		else:
			print(i)