#!/usr/bin/env python3
import time, logging, os, ast

logger = logging.getLogger()
logging.basicConfig(format="%(levelname)9s:%(filename)s:%(message)s")
logger.setLevel(logging.DEBUG)

def hook(l=None):
    if l:
        locals().update(l)
    import IPython
    IPython.embed(banner1="", confirm_exit=False)
    exit(0)

BITS=6
MAXVAL = 2**BITS
MAXROW = 2**(BITS//2)

def fmt_merge(hi,lo):
	return (hi<<(BITS//2))|lo

def fmt_split(x):
	mask = (1<<(BITS//2))-1
	return (x>>(BITS//2))&mask, x&mask

def check(sbox):
	if set(sbox)!=set(range(MAXVAL)):
		return False
	lo, hi = zip(*map(fmt_split,sbox))
	row_vals = set(range(MAXROW))
	for l in lo,hi:
		for i in range(MAXROW):
			row = l[i*MAXROW:(i+1)*MAXROW]
			if set(row)!=row_vals:
				return False
			col = l[i::MAXROW]
			if set(col)!=row_vals:
				return False
	return True

def idx_options(avail,x):
	i,j = fmt_split(x)
	hi = avail['hi']['row'][i].intersection(avail['hi']['col'][j])
	lo = avail['lo']['row'][i].intersection(avail['lo']['col'][j])
	a = set()
	for x,y in map(fmt_split,avail['all']):
		if x in hi and y in lo:
			if x!=MAXROW or hi<lo:
				a.add(fmt_merge(x,y))
	return a

def unit_propigation(seen,assignments,avail,last=False):
	logger.debug("Propigate(%r)", locals())
	for idx, v, level in assignments if not last else assignments[-1:]:
		x,y = fmt_split(v)
		avail['all'].remove(v)
		i,j = fmt_split(idx)
		avail['hi']['row'][i].discard(x)
		avail['hi']['col'][j].discard(x)
		avail['lo']['row'][i].discard(y)
		avail['lo']['col'][j].discard(y)
		seen.add(idx)
	for x in range(MAXVAL):
		if x in seen:
			continue
		s = idx_options(avail,x)
		#if there is only one choice, append to assignments
		if len(s)==1:
			#make assignment
			assignments.append((x,list(s)[0],assignments[-1][-1]))
			logger.debug("Learned: %r", assignments[-1])
			#recursively propigate
			return unit_propigation(seen,assignments,avail,True)
		if len(s)==0:
			#CONFLICT
			logger.debug("CONFLICT %r", assignments)
			return False
	return True

def backtrack(seen,assignments,avail,level):
	logger.debug("Backtrack(%r)", locals())
	#pop from assignments until at level
	idx,v,l = assignments.pop()
	while l>=level:
		#remove from seen
		seen.discard(idx)
		#add back to avail (all, lo/hi, row/col)
		avail['all'].add(v)
		x,y = fmt_split(v)
		i,j = fmt_split(idx)
		avail['hi']['row'][i].add(x)
		avail['hi']['col'][j].add(x)
		avail['lo']['row'][i].add(y)
		avail['lo']['col'][j].add(y)
		idx,v,l = assignments.pop()
	assignments.append((idx,v,l))
	#logger.debug("after_backtrack: %r",locals())

def pick_branching_var(seen,avail):
	for i in range(MAXVAL):
		if i not in seen:
			logger.debug("Branching on %d", i)
			return i, idx_options(avail,i)
	logger.error("Unable to select branching variable.")
	exit(2)

if __name__ == "__main__":
	avail = {
		"hi":{
			"row": {x:set(range(MAXROW)) for x in range(MAXROW)},
			"col": {x:set(range(MAXROW)) for x in range(MAXROW)}
		},
		"lo":{
			"row": {x:set(range(MAXROW)) for x in range(MAXROW)},
			"col": {x:set(range(MAXROW)) for x in range(MAXROW)}
		},
		"all": set(range(MAXVAL))
	}
	#start with the equivilance class first row 00, 11, 22, ..
	seen = set()
	assignments = [(x,fmt_merge(x,x), -1) for x in range(MAXROW)]
	assignment_state = []
	tried = set()
	if not unit_propigation(seen,assignments,avail):
		logger.error("Initial conditions unsat")
		exit(1)
	while len(assignments)!=MAXVAL:
		idx, vals = pick_branching_var(seen,avail)
		cur_level = assignments[-1][-1]+1
		for x in vals:
			if x in tried:
				continue
			assignments.append((idx,x,cur_level))
			logger.debug("Made branch assignment: %r", assignments[-1])
			tried.add(x)
			if unit_propigation(seen,assignments,avail,True):
				assignment_state.append(tried)
				tried = set()
				break
			else:
				backtrack(seen, assignments, avail, cur_level)
				assignments.append((idx,x,cur_level))
		else:
			#uh oh backtrack cur_level-1 but ensure we do not make the same selection
			logger.debug("multi-level backtrack")
			if not assignment_state:
				hook(locals())
			tried = assignment_state.pop()
			backtrack(seen, assignments, avail, cur_level-1)
	hook(locals())
