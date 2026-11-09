/*
 * UCM Native Core I64 profile v0.1.
 *
 * Dependency-free C17 execution realization for a closed, effect-free UCL
 * constitutional core.  Python authors and verifies the canonical projection;
 * this runtime independently checks its denominator and SHA-256 commitment,
 * then executes with fixed storage and checked signed arithmetic.
 *
 * SPDX-License-Identifier: Apache-2.0
 */
#include <errno.h>
#include <inttypes.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_INSTRUCTIONS 4096
#define MAX_REGISTERS 256
#define MAX_STACK 1024
#define MAX_LINE 8192

typedef struct { uint32_t h[8]; uint64_t bits; unsigned char block[64]; size_t used; } sha256_ctx;
static uint32_t rotr(uint32_t x,unsigned n){return (x>>n)|(x<<(32U-n));}
static uint32_t load32(const unsigned char*p){return((uint32_t)p[0]<<24)|((uint32_t)p[1]<<16)|((uint32_t)p[2]<<8)|p[3];}
static void store32(unsigned char*p,uint32_t x){p[0]=(unsigned char)(x>>24);p[1]=(unsigned char)(x>>16);p[2]=(unsigned char)(x>>8);p[3]=(unsigned char)x;}
static const uint32_t K[64]={
0x428a2f98U,0x71374491U,0xb5c0fbcfU,0xe9b5dba5U,0x3956c25bU,0x59f111f1U,0x923f82a4U,0xab1c5ed5U,
0xd807aa98U,0x12835b01U,0x243185beU,0x550c7dc3U,0x72be5d74U,0x80deb1feU,0x9bdc06a7U,0xc19bf174U,
0xe49b69c1U,0xefbe4786U,0x0fc19dc6U,0x240ca1ccU,0x2de92c6fU,0x4a7484aaU,0x5cb0a9dcU,0x76f988daU,
0x983e5152U,0xa831c66dU,0xb00327c8U,0xbf597fc7U,0xc6e00bf3U,0xd5a79147U,0x06ca6351U,0x14292967U,
0x27b70a85U,0x2e1b2138U,0x4d2c6dfcU,0x53380d13U,0x650a7354U,0x766a0abbU,0x81c2c92eU,0x92722c85U,
0xa2bfe8a1U,0xa81a664bU,0xc24b8b70U,0xc76c51a3U,0xd192e819U,0xd6990624U,0xf40e3585U,0x106aa070U,
0x19a4c116U,0x1e376c08U,0x2748774cU,0x34b0bcb5U,0x391c0cb3U,0x4ed8aa4aU,0x5b9cca4fU,0x682e6ff3U,
0x748f82eeU,0x78a5636fU,0x84c87814U,0x8cc70208U,0x90befffaU,0xa4506cebU,0xbef9a3f7U,0xc67178f2U};
static void sha256_block(sha256_ctx*c,const unsigned char*p){uint32_t w[64],a,b,d,e,f,g,h,i,t1,t2,cc;for(i=0;i<16;i++)w[i]=load32(p+4*i);for(;i<64;i++){uint32_t x=w[i-15],y=w[i-2];w[i]=w[i-16]+(rotr(x,7)^rotr(x,18)^(x>>3))+w[i-7]+(rotr(y,17)^rotr(y,19)^(y>>10));}a=c->h[0];b=c->h[1];cc=c->h[2];d=c->h[3];e=c->h[4];f=c->h[5];g=c->h[6];h=c->h[7];for(i=0;i<64;i++){uint32_t s1=rotr(e,6)^rotr(e,11)^rotr(e,25),ch=(e&f)^((~e)&g);uint32_t s0=rotr(a,2)^rotr(a,13)^rotr(a,22),maj=(a&b)^(a&cc)^(b&cc);t1=h+s1+ch+K[i]+w[i];t2=s0+maj;h=g;g=f;f=e;e=d+t1;d=cc;cc=b;b=a;a=t1+t2;}c->h[0]+=a;c->h[1]+=b;c->h[2]+=cc;c->h[3]+=d;c->h[4]+=e;c->h[5]+=f;c->h[6]+=g;c->h[7]+=h;}
static void sha256_init(sha256_ctx*c){static const uint32_t init[8]={0x6a09e667U,0xbb67ae85U,0x3c6ef372U,0xa54ff53aU,0x510e527fU,0x9b05688cU,0x1f83d9abU,0x5be0cd19U};memcpy(c->h,init,sizeof(init));c->bits=0;c->used=0;}
static void sha256_update(sha256_ctx*c,const unsigned char*p,size_t n){c->bits+=(uint64_t)n*8U;while(n){size_t take=64-c->used;if(take>n)take=n;memcpy(c->block+c->used,p,take);c->used+=take;p+=take;n-=take;if(c->used==64){sha256_block(c,c->block);c->used=0;}}}
static void sha256_final(sha256_ctx*c,unsigned char out[32]){uint64_t bits=c->bits;size_t i;c->block[c->used++]=0x80;if(c->used>56){while(c->used<64)c->block[c->used++]=0;sha256_block(c,c->block);c->used=0;}while(c->used<56)c->block[c->used++]=0;for(i=0;i<8;i++)c->block[63-i]=(unsigned char)(bits>>(8*i));sha256_block(c,c->block);for(i=0;i<8;i++)store32(out+4*i,c->h[i]);}
static void hex32(char out[65],const unsigned char in[32]){static const char x[]="0123456789abcdef";size_t i;for(i=0;i<32;i++){out[2*i]=x[in[i]>>4];out[2*i+1]=x[in[i]&15];}out[64]='\0';}

typedef enum {OP_PUSH,OP_LOAD,OP_STORE,OP_ADD,OP_SUB,OP_MUL,OP_DIV,OP_MOD,OP_EQ,OP_LT,OP_AND,OP_OR,OP_NOT,OP_DUP,OP_DROP,OP_JZ,OP_JMP,OP_HALT} opcode;
typedef struct { opcode op; int64_t arg; } instruction;
static instruction code[MAX_INSTRUCTIONS];
static int64_t regs[MAX_REGISTERS],stack_values[MAX_STACK];

static int refuse(const char*code_text){fprintf(stderr,"%s\n",code_text);return 3;}
static int canonical_u64_text(const char*s){size_t i;if(!s||!*s)return 0;if(*s=='0')return s[1]=='\0';if(*s<'1'||*s>'9')return 0;for(i=1;s[i];i++)if(s[i]<'0'||s[i]>'9')return 0;return 1;}
static int canonical_i64_text(const char*s){if(!s||!*s)return 0;if(*s=='-')return s[1]&&strcmp(s+1,"0")!=0&&canonical_u64_text(s+1);return canonical_u64_text(s);}
static int parse_i64(const char*s,int64_t*out){char*end=NULL;intmax_t v;errno=0;if(!canonical_i64_text(s))return 0;v=strtoimax(s,&end,10);if(errno||!end||*end||v<INT64_MIN||v>INT64_MAX)return 0;*out=(int64_t)v;return 1;}
static int parse_u64(const char*s,uint64_t*out){char*end=NULL;uintmax_t v;errno=0;if(!canonical_u64_text(s))return 0;v=strtoumax(s,&end,10);if(errno||!end||*end)return 0;*out=(uint64_t)v;return 1;}
static int hex64_valid(const char*s){size_t i;if(!s||strlen(s)!=64)return 0;for(i=0;i<64;i++)if(!((s[i]>='0'&&s[i]<='9')||(s[i]>='a'&&s[i]<='f')))return 0;return 1;}
static int hash_file(const char*path,char out[65]){FILE*f=fopen(path,"rb");unsigned char buf[65536],digest[32];size_t n;sha256_ctx c;if(!f)return 0;sha256_init(&c);while((n=fread(buf,1,sizeof(buf),f))>0)sha256_update(&c,buf,n);if(ferror(f)){fclose(f);return 0;}fclose(f);sha256_final(&c,digest);hex32(out,digest);return 1;}
static int id_valid(const char*s){size_t i,n=strlen(s);if(n<1||n>128||!((*s>='A'&&*s<='Z')||(*s>='a'&&*s<='z')||*s=='_'))return 0;for(i=1;i<n;i++){char c=s[i];if(!((c>='A'&&c<='Z')||(c>='a'&&c<='z')||(c>='0'&&c<='9')||c=='_'||c=='.'||c==':'||c=='-'))return 0;}return 1;}
static int opcode_of(const char*s,opcode*out,int*has_arg){static const char*names[]={"PUSH","LOAD","STORE","ADD","SUB","MUL","DIV","MOD","EQ","LT","AND","OR","NOT","DUP","DROP","JZ","JMP","HALT"};size_t i;for(i=0;i<sizeof(names)/sizeof(names[0]);i++)if(strcmp(s,names[i])==0){*out=(opcode)i;*has_arg=(i<=OP_STORE||i==OP_JZ||i==OP_JMP);return 1;}return 0;}
static int add_checked(int64_t a,int64_t b,int64_t*out){if((b>0&&a>INT64_MAX-b)||(b<0&&a<INT64_MIN-b))return 0;*out=a+b;return 1;}
static int sub_checked(int64_t a,int64_t b,int64_t*out){if((b<0&&a>INT64_MAX+b)||(b>0&&a<INT64_MIN+b))return 0;*out=a-b;return 1;}
static int mul_checked(int64_t a,int64_t b,int64_t*out){if(a==0||b==0){*out=0;return 1;}if((a==-1&&b==INT64_MIN)||(b==-1&&a==INT64_MIN))return 0;if(a>0){if((b>0&&a>INT64_MAX/b)||(b<0&&b<INT64_MIN/a))return 0;}else{if((b>0&&a<INT64_MIN/b)||(b<0&&a<INT64_MAX/b))return 0;}*out=a*b;return 1;}

int main(int argc,char**argv){
    FILE*f;char line[MAX_LINE],program_id[129],expected_code[65],actual_code[65],expected_body[65],actual_body[65],program_sha[65];
    size_t register_count=0,instruction_count=0,read_count=0,sp=0,pc=0;uint64_t max_steps=0,steps=0,trailer_count=0;
    sha256_ctx body_hash,code_hash;unsigned char digest[32];int in_code=0,have_end=0;
    if(argc!=3){fprintf(stderr,"usage: %s PROGRAM.ucln EXPECTED_PROGRAM_SHA256\n",argv[0]);return 64;}
    if(!hex64_valid(argv[2]))return refuse("NATIVE_EXPECTED_PROGRAM_ROOT_INVALID");
    if(!hash_file(argv[1],program_sha))return refuse("NATIVE_PROGRAM_OPEN_FAILED");
    if(strcmp(program_sha,argv[2])!=0)return refuse("NATIVE_PROGRAM_ROOT_MISMATCH");
    f=fopen(argv[1],"rb");if(!f)return refuse("NATIVE_PROGRAM_OPEN_FAILED");sha256_init(&body_hash);sha256_init(&code_hash);
#define READ_HEADER(prefix) do{if(!fgets(line,sizeof(line),f)){fclose(f);return refuse("NATIVE_PROGRAM_TRUNCATED");}sha256_update(&body_hash,(unsigned char*)line,strlen(line));if(strncmp(line,prefix,strlen(prefix))!=0){fclose(f);return refuse("NATIVE_PROGRAM_HEADER_INVALID");}}while(0)
    READ_HEADER("UCM-NATIVE-CORE\t1\tI64\n");
    READ_HEADER("PROGRAM\t");line[strcspn(line,"\r\n")]='\0';if(!id_valid(line+8)){fclose(f);return refuse("NATIVE_PROGRAM_ID_INVALID");}strcpy(program_id,line+8);
    READ_HEADER("REGISTERS\t");{char*tok;uint64_t declared=0,i=0;line[strcspn(line,"\r\n")]='\0';tok=strtok(line+10,"\t");if(!tok||!parse_u64(tok,&declared)||declared>MAX_REGISTERS){fclose(f);return refuse("NATIVE_REGISTER_SET_INVALID");}while((tok=strtok(NULL,"\t"))!=NULL){if(i>=declared||!parse_i64(tok,&regs[i])){fclose(f);return refuse("NATIVE_REGISTER_VALUE_INVALID");}i++;}if(i!=declared){fclose(f);return refuse("NATIVE_REGISTER_COUNT_MISMATCH");}register_count=(size_t)declared;}
    READ_HEADER("MAX_STEPS\t");line[strcspn(line,"\r\n")]='\0';if(!parse_u64(line+10,&max_steps)||max_steps<1||max_steps>1000000){fclose(f);return refuse("NATIVE_STEP_BOUND_INVALID");}
    READ_HEADER("INSTRUCTIONS\t");line[strcspn(line,"\r\n")]='\0';{uint64_t n;if(!parse_u64(line+13,&n)||n<1||n>MAX_INSTRUCTIONS){fclose(f);return refuse("NATIVE_INSTRUCTION_SET_INVALID");}instruction_count=(size_t)n;}
    READ_HEADER("CODE_SHA256\t");line[strcspn(line,"\r\n")]='\0';if(!hex64_valid(line+12)){fclose(f);return refuse("NATIVE_CODE_DIGEST_INVALID");}strcpy(expected_code,line+12);
    READ_HEADER("BEGIN\n");in_code=1;
    while(fgets(line,sizeof(line),f)){
        if(strncmp(line,"END\t",4)==0){char*tok;line[strcspn(line,"\r\n")]='\0';tok=strtok(line+4,"\t");if(!tok||!parse_u64(tok,&trailer_count)||(tok=strtok(NULL,"\t"))==NULL||!hex64_valid(tok)||strtok(NULL,"\t")!=NULL){fclose(f);return refuse("NATIVE_TRAILER_INVALID");}strcpy(expected_body,tok);have_end=1;break;}
        if(!in_code||read_count>=instruction_count){fclose(f);return refuse("NATIVE_INSTRUCTION_COUNT_MISMATCH");}
        sha256_update(&body_hash,(unsigned char*)line,strlen(line));sha256_update(&code_hash,(unsigned char*)line,strlen(line));
        line[strcspn(line,"\r\n")]='\0';{char*tab=strchr(line,'\t');char*arg_text=NULL;int has_arg=0;if(tab){*tab='\0';arg_text=tab+1;}if(!opcode_of(line,&code[read_count].op,&has_arg)||(has_arg!=(arg_text!=NULL))||(has_arg&&!parse_i64(arg_text,&code[read_count].arg))){fclose(f);return refuse("NATIVE_INSTRUCTION_INVALID");}if((code[read_count].op==OP_LOAD||code[read_count].op==OP_STORE)&&(code[read_count].arg<0||(uint64_t)code[read_count].arg>=register_count)){fclose(f);return refuse("NATIVE_REGISTER_INDEX_INVALID");}if((code[read_count].op==OP_JZ||code[read_count].op==OP_JMP)&&(code[read_count].arg<0||(uint64_t)code[read_count].arg>=instruction_count)){fclose(f);return refuse("NATIVE_JUMP_TARGET_INVALID");}}read_count++;
    }
    if(have_end&&fgetc(f)!=EOF){fclose(f);return refuse("NATIVE_TRAILING_DATA_REFUSED");}
    fclose(f);if(!have_end||read_count!=instruction_count||trailer_count!=instruction_count||code[instruction_count-1].op!=OP_HALT)return refuse("NATIVE_DENOMINATOR_MISMATCH");
    sha256_final(&code_hash,digest);hex32(actual_code,digest);if(strcmp(actual_code,expected_code)!=0)return refuse("NATIVE_CODE_DIGEST_MISMATCH");
    sha256_final(&body_hash,digest);hex32(actual_body,digest);if(strcmp(actual_body,expected_body)!=0)return refuse("NATIVE_BODY_DIGEST_MISMATCH");
    while(1){instruction ins;int64_t a,b,r;if(pc>=instruction_count)return refuse("NATIVE_PC_INVALID");if(++steps>max_steps)return refuse("NATIVE_STEP_BOUND_EXHAUSTED");ins=code[pc++];
#define POP(v) do{if(sp==0)return refuse("NATIVE_STACK_UNDERFLOW");(v)=stack_values[--sp];}while(0)
#define PUSH(v) do{if(sp>=MAX_STACK)return refuse("NATIVE_STACK_BOUND_EXHAUSTED");stack_values[sp++]=(v);}while(0)
        switch(ins.op){
        case OP_PUSH:PUSH(ins.arg);break;case OP_LOAD:PUSH(regs[ins.arg]);break;case OP_STORE:POP(a);regs[ins.arg]=a;break;
        case OP_DUP:if(sp==0)return refuse("NATIVE_STACK_UNDERFLOW");a=stack_values[sp-1];PUSH(a);break;case OP_DROP:POP(a);break;
        case OP_NOT:POP(a);if(a!=0&&a!=1)return refuse("NATIVE_BOOL_REQUIRED");PUSH(1-a);break;
        case OP_ADD:POP(b);POP(a);if(!add_checked(a,b,&r))return refuse("NATIVE_I64_OVERFLOW");PUSH(r);break;
        case OP_SUB:POP(b);POP(a);if(!sub_checked(a,b,&r))return refuse("NATIVE_I64_OVERFLOW");PUSH(r);break;
        case OP_MUL:POP(b);POP(a);if(!mul_checked(a,b,&r))return refuse("NATIVE_I64_OVERFLOW");PUSH(r);break;
        case OP_DIV:case OP_MOD:POP(b);POP(a);if(b==0)return refuse("NATIVE_DIVISION_BY_ZERO");if(a==INT64_MIN&&b==-1)return refuse("NATIVE_I64_OVERFLOW");r=(ins.op==OP_DIV)?a/b:a%b;PUSH(r);break;
        case OP_EQ:POP(b);POP(a);PUSH(a==b);break;case OP_LT:POP(b);POP(a);PUSH(a<b);break;
        case OP_AND:case OP_OR:POP(b);POP(a);if((a!=0&&a!=1)||(b!=0&&b!=1))return refuse("NATIVE_BOOL_REQUIRED");PUSH(ins.op==OP_AND?(a&b):(a|b));break;
        case OP_JZ:POP(a);if(a!=0&&a!=1)return refuse("NATIVE_BOOL_REQUIRED");if(a==0)pc=(size_t)ins.arg;break;case OP_JMP:pc=(size_t)ins.arg;break;
        case OP_HALT:if(sp!=1)return refuse("NATIVE_TERMINAL_STACK_INVALID");printf("{\"program_sha256\":\"%s\",\"result_i64\":%" PRId64 ",\"status\":\"PASS\",\"steps\":%" PRIu64 "}\n",program_sha,stack_values[0],steps);return 0;
        default:return refuse("NATIVE_OPCODE_UNKNOWN");}
    }
}
