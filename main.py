from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf

app = FastAPI()

# HTML 화면이 파이썬 서버에 접근할 수 있도록 보안문을 열어주는 설정 (CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "서버가 정상적으로 작동 중입니다!"}

# 1. 실시간 주가 가져오기 기능
@app.get("/api/market-data/{ticker}")
def get_market_data(ticker: str):
    stock = yf.Ticker(ticker)
    current_price = stock.fast_info['last_price']
    return {
        "ticker": ticker.upper(),
        "current_price": round(current_price, 2),
        "status": "success"
    }

# 2. 실시간 장세 분석 및 뉴스 수집 기능
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

    # 야후 파이낸스에서 최신 뉴스 헤드라인 5개 긁어오기
    news_data = stock.news
    news_list = []
    if news_data:
        for news in news_data[:5]:
            title = news.get('title', '제목 없음')
            news_list.append(title)
    else:
        news_list.append("현재 업데이트된 주요 뉴스가 없습니다.")

    return {
        "ticker": ticker.upper(),
        "bull_prob": bull,
        "sideways_prob": sideways,
        "bear_prob": bear,
        "description": desc,
        "news": news_list
    }
