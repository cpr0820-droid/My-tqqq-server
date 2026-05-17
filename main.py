from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import yfinance as yf
import google.generativeai as genai
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
else:
    ai_model = None

def extract_title(news_dict):
    for key in ['title', 'headline', 'summary', 'text']:
        if news_dict.get(key): return news_dict[key]
    return "최신 시장 이슈"

def ai_translate_and_explain(headlines, ticker):
    if not ai_model:
        return [f"⚠️ [비밀키 미인식] Render 설정에서 GEMINI_API_KEY를 확인하세요: {h}" for h in headlines]
    
    prompt = f"""
    너는 주식 초보자(주린이)들을 위한 친절한 금융 전문 AI 비서야.
    아래의 미국 주식 시장 최신 뉴스 헤드라인 5개를 읽고, 주린이 눈높이에 맞춰 다음 규칙대로 변환해 줘.

    [규칙]
    1. 각 뉴스의 핵심 내용을 친절한 한국어로 번역 및 요약해 줘.
    2. 이 뉴스가 왜 '{ticker}' 투자자에게 중요한지, 호재인지 악재인지 1~2문장으로 아주 쉽게 해설해 줘.
    3. 전문 용어(금리 인상, 매파 등)가 있다면 주린이가 이해하기 쉽게 풀어서 설명해 줘.
    4. 반드시 아래 예시처럼 각 뉴스별로 <li> 태그 안에 들어갈 깔끔한 한 줄 문장 형태로만 딱 5줄 반환해 줘. 다른 인사말은 절대 하지 마.

    [반환 예시]
    📢 [뉴스 요약] - 해설 내용
    """
    
    for i, h in enumerate(headlines, 1):
        prompt += f"\n뉴스 {i}: {h}"
        
    try:
        response = ai_model.generate_content(prompt)
        lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        return lines[:5]
    except Exception as e:
        # 💡 [핵심 변경점] 단순히 지연되었다고 뭉뚱그리지 않고, 진짜 에러 원인(str(e))을 화면에 내보냅니다!
        return [f"❌ AI 에러 발생 ({str(e)}): {h}" for h in headlines]

@app.get("/")
def read_root():
    return {"message": "서버가 정상적으로 작동 중입니다!"}

@app.get("/api/market-data/{ticker}")
def get_market_data(ticker: str):
    stock = yf.Ticker(ticker)
    current_price = stock.fast_info['last_price']
    return {"ticker": ticker.upper(), "current_price": round(current_price, 2), "status": "success"}

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
    if search_ticker == "TQQQ": search_ticker = "QQQ"
    elif search_ticker == "SOXL": search_ticker = "SOXX"

    news_stock = yf.Ticker(search_ticker)
    news_data = news_stock.news
    if not news_data: news_data = yf.Ticker("SPY").news

    raw_headlines = []
    if news_data:
        for news in news_data[:5]:
            raw_headlines.append(extract_title(news))
    else:
        raw_headlines.append("현재 미국 시장에 특별한 주요 뉴스가 없습니다.")

    smart_news = ai_translate_and_explain(raw_headlines, ticker.upper())

    return {
        "ticker": ticker.upper(),
        "bull_prob": bull,
        "sideways_prob": sideways,
        "bear_prob": bear,
        "description": desc,
        "news": smart_news
    }
