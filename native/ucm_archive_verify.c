/*
 * UCM v0.1 native archive verifier slice.
 *
 * This deliberately small C11 program verifies the SHA-256 compatibility
 * projection emitted by `pippi archive-native-manifest`.  The Python reference
 * verifier remains responsible for BLAKE3, THR and DKN records.  Keeping these
 * scopes explicit prevents the native slice from overclaiming equivalence.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#include <errno.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct { uint32_t h[8]; uint64_t bits; unsigned char block[64]; size_t used; } sha256_ctx;

static uint32_t rotr(uint32_t x, unsigned n) { return (x >> n) | (x << (32U - n)); }
static uint32_t load32(const unsigned char *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) | ((uint32_t)p[2] << 8) | p[3];
}
static void store32(unsigned char *p, uint32_t x) {
    p[0]=(unsigned char)(x>>24); p[1]=(unsigned char)(x>>16); p[2]=(unsigned char)(x>>8); p[3]=(unsigned char)x;
}
static const uint32_t K[64] = {
  0x428a2f98U,0x71374491U,0xb5c0fbcfU,0xe9b5dba5U,0x3956c25bU,0x59f111f1U,0x923f82a4U,0xab1c5ed5U,
  0xd807aa98U,0x12835b01U,0x243185beU,0x550c7dc3U,0x72be5d74U,0x80deb1feU,0x9bdc06a7U,0xc19bf174U,
  0xe49b69c1U,0xefbe4786U,0x0fc19dc6U,0x240ca1ccU,0x2de92c6fU,0x4a7484aaU,0x5cb0a9dcU,0x76f988daU,
  0x983e5152U,0xa831c66dU,0xb00327c8U,0xbf597fc7U,0xc6e00bf3U,0xd5a79147U,0x06ca6351U,0x14292967U,
  0x27b70a85U,0x2e1b2138U,0x4d2c6dfcU,0x53380d13U,0x650a7354U,0x766a0abbU,0x81c2c92eU,0x92722c85U,
  0xa2bfe8a1U,0xa81a664bU,0xc24b8b70U,0xc76c51a3U,0xd192e819U,0xd6990624U,0xf40e3585U,0x106aa070U,
  0x19a4c116U,0x1e376c08U,0x2748774cU,0x34b0bcb5U,0x391c0cb3U,0x4ed8aa4aU,0x5b9cca4fU,0x682e6ff3U,
  0x748f82eeU,0x78a5636fU,0x84c87814U,0x8cc70208U,0x90befffaU,0xa4506cebU,0xbef9a3f7U,0xc67178f2U
};
static void sha256_block(sha256_ctx *c, const unsigned char *p) {
    uint32_t w[64],a,b,d,e,f,g,h,i,t1,t2,cc;
    for (i=0;i<16;i++) w[i]=load32(p+4*i);
    for (;i<64;i++) { uint32_t x=w[i-15],y=w[i-2];
        w[i]=w[i-16]+(rotr(x,7)^rotr(x,18)^(x>>3))+w[i-7]+(rotr(y,17)^rotr(y,19)^(y>>10)); }
    a=c->h[0];b=c->h[1];cc=c->h[2];d=c->h[3];e=c->h[4];f=c->h[5];g=c->h[6];h=c->h[7];
    for (i=0;i<64;i++) { uint32_t s1=rotr(e,6)^rotr(e,11)^rotr(e,25),ch=(e&f)^((~e)&g);
        uint32_t s0=rotr(a,2)^rotr(a,13)^rotr(a,22),maj=(a&b)^(a&cc)^(b&cc);
        t1=h+s1+ch+K[i]+w[i];t2=s0+maj;h=g;g=f;f=e;e=d+t1;d=cc;cc=b;b=a;a=t1+t2; }
    c->h[0]+=a;c->h[1]+=b;c->h[2]+=cc;c->h[3]+=d;c->h[4]+=e;c->h[5]+=f;c->h[6]+=g;c->h[7]+=h;
}
static void sha256_init(sha256_ctx *c) {
    static const uint32_t init[8]={0x6a09e667U,0xbb67ae85U,0x3c6ef372U,0xa54ff53aU,0x510e527fU,0x9b05688cU,0x1f83d9abU,0x5be0cd19U};
    memcpy(c->h,init,sizeof(init));c->bits=0;c->used=0;
}
static void sha256_update(sha256_ctx *c,const unsigned char *p,size_t n) {
    c->bits += (uint64_t)n*8U;
    while(n){size_t take=64-c->used;if(take>n)take=n;memcpy(c->block+c->used,p,take);c->used+=take;p+=take;n-=take;
        if(c->used==64){sha256_block(c,c->block);c->used=0;}}
}
static void sha256_final(sha256_ctx *c,unsigned char out[32]) {
    uint64_t bits=c->bits;size_t i;c->block[c->used++]=0x80;
    if(c->used>56){while(c->used<64)c->block[c->used++]=0;sha256_block(c,c->block);c->used=0;}
    while(c->used<56)c->block[c->used++]=0;
    for(i=0;i<8;i++) c->block[63-i]=(unsigned char)(bits>>(8*i));
    sha256_block(c,c->block);
    for(i=0;i<8;i++)store32(out+4*i,c->h[i]);
}
static void hex32(char out[65],const unsigned char in[32]) {
    static const char x[]="0123456789abcdef";size_t i;
    for(i=0;i<32;i++){out[2*i]=x[in[i]>>4];out[2*i+1]=x[in[i]&15];}out[64]='\0';
}
static int hex64_valid(const char *s) {
    size_t i;if(!s||strlen(s)!=64)return 0;
    for(i=0;i<64;i++)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return 0;
    return 1;
}
static int portable_path(const char *p) {
    const char *q=p;if(!*p||*p=='/'||*p=='\\')return 0;
    if(strlen(p)>4096||strchr(p,'\\')||strchr(p,'\t')||strchr(p,'\r')||strchr(p,'\n'))return 0;
    while(*q){if((q==p||q[-1]=='/')&&q[0]=='.'&&(q[1]=='/'||q[1]=='\0'||(q[1]=='.'&&(q[2]=='/'||q[2]=='\0'))))return 0;q++;}
    return 1;
}
static int hash_file(const char *path,char actual[65],uint64_t *size) {
    unsigned char buf[65536],digest[32];size_t n;FILE *f=fopen(path,"rb");sha256_ctx c;*size=0;
    if(!f) return 0;
    sha256_init(&c);while((n=fread(buf,1,sizeof(buf),f))>0){sha256_update(&c,buf,n);*size+=(uint64_t)n;}
    if(ferror(f)){fclose(f);return 0;}fclose(f);sha256_final(&c,digest);hex32(actual,digest);return 1;
}
static int join_path(char **out,const char *root,const char *relative) {
    size_t a=strlen(root),b=strlen(relative);if(a>SIZE_MAX-b-2)return 0;*out=(char*)malloc(a+b+2);if(!*out)return 0;
    memcpy(*out,root,a);(*out)[a]='/';memcpy(*out+a+1,relative,b+1);return 1;
}
int main(int argc,char **argv) {
    FILE *mf;char *line=NULL;size_t cap=0;unsigned long line_no=0,checked=0,declared=0,trailer_count=0;int failed=0,ended=0;
    unsigned long externally_expected_count=0;char *count_end=NULL;
    char manifest_root[65]={0},expected_rows_root[65]={0},actual_rows_root[65];sha256_ctx rows_hash;
    if(argc!=6){fprintf(stderr,"usage: %s MANIFEST ROOT EXPECTED_MANIFEST_ROOT EXPECTED_ROWS_ROOT EXPECTED_MEMBER_COUNT\n",argv[0]);return 64;}
    errno=0;externally_expected_count=strtoul(argv[5],&count_end,10);
    if(!hex64_valid(argv[3])){fprintf(stderr,"NATIVE_EXPECTED_MANIFEST_ROOT_INVALID\n");return 64;}
    if(!hex64_valid(argv[4])){fprintf(stderr,"NATIVE_EXPECTED_ROWS_ROOT_INVALID\n");return 64;}
    if(errno||!count_end||*count_end||externally_expected_count==0){fprintf(stderr,"NATIVE_EXPECTED_DENOMINATOR_INVALID\n");return 64;}
    mf=fopen(argv[1],"rb");if(!mf){fprintf(stderr,"NATIVE_MANIFEST_OPEN_FAILED:%d\n",errno);return 74;}
    sha256_init(&rows_hash);
    while(1){int ch;size_t n=0;if(!line){cap=4096;line=(char*)malloc(cap);if(!line){fclose(mf);return 70;}}
        while((ch=fgetc(mf))!=EOF&&ch!='\n'){if(n+1>=cap){char *next;size_t nc=cap*2;if(nc>1024*1024){failed=1;break;}next=(char*)realloc(line,nc);if(!next){failed=1;break;}line=next;cap=nc;}line[n++]=(char)ch;}
        if(failed) break;
        if(ch==EOF&&n==0) break;
        line[n]='\0';line_no++;
        if(line_no==1){char *tok,*end=NULL;tok=strtok(line,"\t");if(!tok||strcmp(tok,"UCM-NATIVE-MANIFEST")!=0||(tok=strtok(NULL,"\t"))==NULL||strcmp(tok,"2")!=0||(tok=strtok(NULL,"\t"))==NULL||strcmp(tok,"SHA-256")!=0||(tok=strtok(NULL,"\t"))==NULL||!hex64_valid(tok)){failed=1;fprintf(stderr,"NATIVE_MANIFEST_HEADER_INVALID\n");break;}strcpy(manifest_root,tok);tok=strtok(NULL,"\t");if(!tok||strtok(NULL,"\t")!=NULL){failed=1;fprintf(stderr,"NATIVE_MANIFEST_HEADER_INVALID\n");break;}errno=0;declared=strtoul(tok,&end,10);if(errno||!end||*end||declared==0||declared!=externally_expected_count||strcmp(manifest_root,argv[3])!=0){failed=1;fprintf(stderr,"NATIVE_MANIFEST_DENOMINATOR_INVALID\n");break;}continue;}
        if(strncmp(line,"END\t",4)==0){char *tok,*end=NULL;unsigned char out[32];tok=strtok(line+4,"\t");if(!tok){failed=1;fprintf(stderr,"NATIVE_MANIFEST_TRAILER_INVALID\n");break;}errno=0;trailer_count=strtoul(tok,&end,10);tok=strtok(NULL,"\t");if(errno||!end||*end||!tok||!hex64_valid(tok)||strtok(NULL,"\t")!=NULL){failed=1;fprintf(stderr,"NATIVE_MANIFEST_TRAILER_INVALID\n");break;}strcpy(expected_rows_root,tok);sha256_final(&rows_hash,out);hex32(actual_rows_root,out);if(trailer_count!=declared||checked!=declared||strcmp(actual_rows_root,expected_rows_root)!=0||strcmp(actual_rows_root,argv[4])!=0){failed=1;fprintf(stderr,"NATIVE_MANIFEST_DENOMINATOR_MISMATCH\n");break;}ended=1;break;}
        sha256_update(&rows_hash,(unsigned char*)line,n);sha256_update(&rows_hash,(const unsigned char*)"\n",1);
        {char *t1=strchr(line,'\t'),*t2;char *path,*full=NULL,*end=NULL,actual[65];uint64_t expected_size,actual_size;
            if(!t1||(t2=strchr(t1+1,'\t'))==NULL){failed=1;fprintf(stderr,"NATIVE_MANIFEST_ROW_INVALID:%lu\n",line_no);break;}
            *t1='\0';*t2='\0';path=t2+1;if(strlen(line)!=64||!portable_path(path)){failed=1;fprintf(stderr,"NATIVE_MANIFEST_ROW_INVALID:%lu\n",line_no);break;}
            errno=0;expected_size=strtoull(t1+1,&end,10);if(errno||!end||*end){failed=1;fprintf(stderr,"NATIVE_SIZE_INVALID:%lu\n",line_no);break;}
            if(!join_path(&full,argv[2],path)||!hash_file(full,actual,&actual_size)){free(full);failed=1;fprintf(stderr,"NATIVE_FILE_READ_FAILED:%s\n",path);break;}
            free(full);if(actual_size!=expected_size||strcmp(actual,line)!=0){failed=1;fprintf(stderr,"NATIVE_DIGEST_MISMATCH:%s\n",path);break;}checked++;}
    }
    if(ended&&fgetc(mf)!=EOF){failed=1;fprintf(stderr,"NATIVE_MANIFEST_TRAILING_DATA_REFUSED\n");}
    free(line);fclose(mf);
    if(failed||!ended)return 3;
    printf("{\"authority_effect\":\"NONE\",\"checked\":%lu,\"g0\":\"CLOSED\",\"manifest_root\":\"%s\",\"rows_root\":\"%s\",\"real_a5\":false,\"standing\":\"INFORMATION_ONLY\",\"status\":\"PASS\"}\n",checked,manifest_root,actual_rows_root);
    return 0;
}
