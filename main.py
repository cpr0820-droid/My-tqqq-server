from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 💡 어떤 구조로 뉴스가 바뀌어도 제목을 찾아내는 무적의 탐지기 함수
def extract_title(news_dict):
    # 1단계: 가장 흔한 핵심 키 단독 확인
    for key in ['title', 'headline', 'summary', 'text']:
        if news_dict.get(key):
            return news_dict[key]
    
    # 2단계: content 폴더 같은 2중 구조 안에 숨겨둔 경우 확인
    if 'content' in news_dict and isinstance(news_dict['content'], dict):
        for key in ['title', 'headline', 'summary']:
            if news_dict['content'].get(key):
                return news_dict['content'][key]
    
    # 3단계: 다 안되면 딕셔너리 내부를 샅샅이 뒤져서 가장 그럴듯한 문장 추출
    all_strings = []
    def search_deep(data):
        if isinstance(data, dict):
            for v in data.values(): search_deep(v)
        elif isinstance(data, list):
            for v in data: search_deep(v)
        elif isinstance(data, str):
            all_strings.append(data)
    
    search_deep(news_dict)
    # 링크(http)가 아니고 글자 수가 15자 이상인 가장 첫 번째 문장을 제목으로 인정
    valid_sentences = [s for s in all_strings if len(s) > 15 and not s.startswith('http')]
    if valid_sentences:
        return valid_sentences[0]
        
    return "최신 미국 시장 주요 이슈"

@app.get("/")
def read_root():
    return {"message": "서버가 정상적으로 작동 중입니다!"}

@app.get("/api/market-data/{ticker}")
def get_market_data(ticker: str):
    stock = yf.Ticker(ticker)
    current_price = stock.fast_info['last_price']
    return {
        "ticker": ticker.upper(),
        "current_price": round(current_price, 2),
        "status": "success"
    }

@app.get("/api/market-sentiment/{ticker}")
def analyze_market(ticker: str):
    stock = yf.Ticker(ticker)
    hist = stock.history(period="1mo")
    
    if hist.empty:
        return {"error": "데이터를 불러올 수 없습니다."}

    start_price = hist['Close'].iloc[0]
    end_price = hist['Close'].iloc[-1]
    return_rate = ((end_price - start_price) / start_price) * 100
    max_price = hist['Close'].max()
    drawdown = ((end_price - max_price) / max_price) * 100

    if return_rate > 5 and drawdown > -5:
        bull, sideways, bear = 60, 30, 10
        desc = f"최근 1개월간 {ticker}는 {return_rate:.1f}% 상승하며 강한 흐름을 보이고 있습니다. 익절 주기가 짧아지는 긍정적인 장세입니다."
    elif drawdown < -15:
        bull, sideways, bear = 10, 30, 60
        desc = f"최근 고점 대비 {drawdown:.1f}% 하락하며 뚜렷한 하락 추세입니다. 진입을 보수적으로 잡아야 할 시기입니다."
    else:
        bull, sideways, bear = 20, 65, 15
        desc = f"최근 1개월 수익률은 {return_rate:.1f}%로, 위아래로 흔들리는 변동성 횡보장입니다. 무한매수법이 수학적 우위를 갖기 가장 좋습니다."

    search_ticker = ticker.upper()
    if search_ticker == "TQQQ":
        search_ticker = "QQQ"
    elif search_ticker == "SOXL":
        search_ticker = "SOXX"

    news_stock = yf.Ticker(search_ticker)
    news_data = news_stock.news
    
    if not news_data:
        news_data = yf.Ticker("SPY").news

    news_list = []
    if news_data:
        for news in news_data[:5]:
            # 💡 새로 만든 무적의 함수로 제목 추출!
            title = extract_title(news)
            news_list.append(title)
    else:
        news_list.append("현재 업데이트된 주요 시장 뉴스가 없습니다.")

    return {
        "ticker": ticker.upper(),
        "bull_prob": bull,
        "sideways_prob": sideways,
        "bear_prob": bear,
        "description": desc,
        "news": news_list
    }
