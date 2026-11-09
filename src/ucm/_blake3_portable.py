"""Small dependency-free BLAKE3-256 reference path used when `blake3` is absent.

This implements the unkeyed hash mode required by the transtemporal archive.
It intentionally exposes no key-derivation or MAC interface.
"""
from __future__ import annotations
from dataclasses import dataclass
import struct

IV=(0x6A09E667,0xBB67AE85,0x3C6EF372,0xA54FF53A,0x510E527F,0x9B05688C,0x1F83D9AB,0x5BE0CD19)
PERM=(2,6,3,10,7,0,4,13,1,11,12,5,9,14,15,8)
CHUNK_START=1;CHUNK_END=2;PARENT=4;ROOT=8
MASK=0xFFFFFFFF

def _r(x,n):return ((x>>n)|(x<<(32-n)))&MASK
def _g(s,a,b,c,d,x,y):
    s[a]=(s[a]+s[b]+x)&MASK;s[d]=_r(s[d]^s[a],16)
    s[c]=(s[c]+s[d])&MASK;s[b]=_r(s[b]^s[c],12)
    s[a]=(s[a]+s[b]+y)&MASK;s[d]=_r(s[d]^s[a],8)
    s[c]=(s[c]+s[d])&MASK;s[b]=_r(s[b]^s[c],7)
def _round(s,m):
    _g(s,0,4,8,12,m[0],m[1]);_g(s,1,5,9,13,m[2],m[3]);_g(s,2,6,10,14,m[4],m[5]);_g(s,3,7,11,15,m[6],m[7])
    _g(s,0,5,10,15,m[8],m[9]);_g(s,1,6,11,12,m[10],m[11]);_g(s,2,7,8,13,m[12],m[13]);_g(s,3,4,9,14,m[14],m[15])
def _compress(cv,words,counter,block_len,flags):
    s=list(cv)+list(IV[:4])+[counter&MASK,(counter>>32)&MASK,block_len,flags];m=list(words)
    for index in range(7):
        _round(s,m)
        if index!=6:m=[m[i] for i in PERM]
    return tuple((s[i]^s[i+8])&MASK for i in range(8))+tuple((s[i+8]^cv[i])&MASK for i in range(8))
def _words(block):return struct.unpack("<16I",block+b"\0"*(64-len(block)))

@dataclass(frozen=True)
class _Output:
    cv:tuple[int,...];words:tuple[int,...];counter:int;block_len:int;flags:int
    def chaining(self):return _compress(self.cv,self.words,self.counter,self.block_len,self.flags)[:8]
    def root_bytes(self,n=32):
        out=bytearray();counter=0
        while len(out)<n:
            out.extend(struct.pack("<16I",*_compress(self.cv,self.words,counter,self.block_len,self.flags|ROOT)));counter+=1
        return bytes(out[:n])
def _chunk_output(chunk,counter):
    blocks=[chunk[i:i+64] for i in range(0,len(chunk),64)] or [b""];cv=IV
    for index,block in enumerate(blocks):
        flags=(CHUNK_START if index==0 else 0)|(CHUNK_END if index==len(blocks)-1 else 0)
        output=_Output(tuple(cv),_words(block),counter,len(block),flags)
        if index!=len(blocks)-1:cv=output.chaining()
    return output
def _parent(left,right):return _Output(IV,tuple(left)+tuple(right),0,64,PARENT)
def digest(data:bytes)->bytes:
    if type(data) is not bytes:raise TypeError("bytes required")
    chunks=[data[i:i+1024] for i in range(0,len(data),1024)] or [b""];stack=[]
    for index,chunk in enumerate(chunks[:-1]):
        cv=_chunk_output(chunk,index).chaining();total=index+1
        while total&1==0:cv=_parent(stack.pop(),cv).chaining();total>>=1
        stack.append(cv)
    output=_chunk_output(chunks[-1],len(chunks)-1)
    while stack:output=_parent(stack.pop(),output.chaining())
    return output.root_bytes(32)
def hexdigest(data:bytes)->str:return digest(data).hex()
