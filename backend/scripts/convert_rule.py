# -*- coding: utf-8 -*-
"""
평서(이다체) → 합쇼체(습니다체) 규칙 변환 1차 엔진.
문장부호(.!?) 기준 문장 분리 후, 각 문장의 '마지막 어절'이 평서 '다'로 끝나면 종결어미만 변환.
문장 중간의 연결형 '다'(내려오다 …)는 건드리지 않음.

이미 손변환된 converted_001/002 의 key 는 건너뜀. 결과 → converted/converted_auto.json
잔존/어색 항목은 이후 사람이 patch 파일로 덮어씀(뒤 파일이 우선되도록 apply가 병합).
"""
import sys, os, io, json, re, glob
sys.path.insert(0, ".")

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CONV_DIR = os.path.join(DATA, "converted")

CHO = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
JUNG = ['ㅏ','ㅐ','ㅑ','ㅒ','ㅓ','ㅔ','ㅕ','ㅖ','ㅗ','ㅘ','ㅙ','ㅚ','ㅛ','ㅜ','ㅝ','ㅞ','ㅟ','ㅠ','ㅡ','ㅢ','ㅣ']
JONG = ['','ㄱ','ㄲ','ㄳ','ㄴ','ㄵ','ㄶ','ㄷ','ㄹ','ㄺ','ㄻ','ㄼ','ㄽ','ㄾ','ㄿ','ㅀ','ㅁ','ㅂ','ㅄ','ㅅ','ㅆ','ㅇ','ㅈ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']

def decompose(s):
    o=ord(s)-0xAC00
    if o<0 or o>11171: return None
    return CHO[o//588], JUNG[(o%588)//28], JONG[o%28]
def compose(cho,jung,jong=''):
    return chr(0xAC00 + CHO.index(cho)*588 + JUNG.index(jung)*28 + JONG.index(jong))

# 정확 접미사 우선 매핑(긴 것 우선)
EXACT = [
    ("이었다","이었습니다"),("았었다","았었습니다"),("었었다","었었습니다"),
    ("이다","입니다"),("아니다","아닙니다"),
    ("있다","있습니다"),("없다","없습니다"),("겠다","겠습니다"),
    ("았다","았습니다"),("었다","었습니다"),("였다","였습니다"),
    ("한다","합니다"),("된다","됩니다"),
    ("같다","같습니다"),("싶다","싶습니다"),
]

# 명사+다 축약 계사(모음 어간이라 규칙이 형용사로 오인) → '입니다'
NOUN_COPULA = (
    "나무다","초화류다","하나다","나리다","정도다","채소다","인기다","솜다리다","냄새다",
    "과실수다","가지가지다","닮아서다","자체다","낭패다","무궁화다","포인트다","히비스커스다",
    "얘기다","열대다","종류다","차지다","수식어다","부추다","여러가지다","배상꽃차례다",
    "애기달래다","비짜루다","고개다","쇠뜨기다","큰꽃으아리다","억새다","고무나무다",
)

def polite_token(tok):
    """어절(마지막 단어)의 종결 '다'를 합쇼체로."""
    for a,b in EXACT:
        if tok.endswith(a):
            return tok[:-len(a)]+b
    if not tok.endswith("다"):
        return tok
    if tok.endswith("는다"):   # 먹는다/받는다/않는다 → 습니다 (ㄴ-받침 분기보다 먼저)
        return tok[:-2]+"습니다"
    for w in NOUN_COPULA:      # 명사+다 계사 → 명사입니다
        if tok.endswith(w):
            return tok[:-1]+"입니다"
    stem_last = tok[-2] if len(tok)>=2 else ''
    d = decompose(stem_last) if stem_last else None
    if d is None:
        # 명사+다 축약(포인트다·睡'다·ephemeral)다) 등 비한글 앞 → 계사 '입니다'
        return tok[:-1]+"입니다"
    cho,jung,jong = d
    if jong=='ㄴ':            # 핀다/간다/된다/보인다 → 피/가/되/보이 + ㅂ니다
        return tok[:-2]+compose(cho,jung,'ㅂ')+"니다"
    if jong=='':             # 크다/예쁘다 → +ㅂ니다
        return tok[:-2]+compose(cho,jung,'ㅂ')+"니다"
    if jong=='ㄹ':           # 살다/만들다 → ㄹ탈락 +ㅂ니다
        return tok[:-2]+compose(cho,jung,'ㅂ')+"니다"
    # 나머지 받침 → +습니다 (좋다/작다/많다/붉다 …). '는다'는 는 제거 후 습니다
    if stem_last=='는':
        return tok[:-2]+"습니다"
    return tok[:-1]+"습니다"

SENT = re.compile(r"([.!?]+|…)")
END_STRIP = '"\'”’‘“()（）~ '

def convert(text):
    # 문장 단위로 순회하며 각 문장 마지막 어절만 변환
    parts = SENT.split(text)
    out=[]
    for seg in parts:
        if SENT.fullmatch(seg) or seg=='':
            out.append(seg); continue
        # seg = 한 문장(공백 포함). 뒤쪽 따옴표/괄호 보존 위해 분리
        m = re.match(r"^(.*?)(\s*)$", seg, re.S)
        core = seg.rstrip()
        trail = seg[len(core):]
        # 끝의 따옴표/괄호 떼고 판정
        rquote=''
        while core and core[-1] in END_STRIP.strip():
            rquote = core[-1]+rquote; core=core[:-1]
        toks = core.split(' ')
        if toks and toks[-1].endswith("다") and not toks[-1].endswith("니다"):
            toks[-1]=polite_token(toks[-1])
        out.append(' '.join(toks)+rquote+trail)
    return ''.join(out)

def main():
    targets=json.load(io.open(os.path.join(DATA,"stories_to_convert.json"),encoding="utf-8"))
    done=set()
    for f in glob.glob(os.path.join(CONV_DIR,"converted_0*.json")):
        done |= set(json.load(io.open(f,encoding="utf-8")).keys())
    res={}
    for t in targets:
        if t["key"] in done: continue
        res[t["key"]]=convert(t["before"])
    out=os.path.join(CONV_DIR,"converted_auto.json")
    json.dump(res, io.open(out,"w",encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"규칙 변환: {len(res)}건 (손변환 제외 {len(done)}건) → {out}")

if __name__=="__main__":
    main()
