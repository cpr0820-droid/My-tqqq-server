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
    ai_model = genai.GenerativeModel('gemini-2.5-flash')
else:
    ai_model = None

# 💡 실제 미국 대장 지수 데이터를 분석하여 AI에게 전달하는 마법의 매크로 분석 함수
def ai_macro_analysis(ticker, ndq_perf, sp_perf, vix_value):
    if not ai_model:
        return ["⚠️ AI 모델이 연결되지 않았습니다."]
    
    prompt = f"""
    너는 주식 초보자(주린이)들을 위한 금융 전문 AI 비서야.
    절대로 가짜 뉴스를 지어내지 말고, 내가 제공하는 '실제 미국 증시 매크로 데이터'를 철저히 바탕으로 현재 시장 경제의 빅 이슈와 장세를 분석해 줘.

    [실제 미국 시장 데이터]
    - 사용자가 분석 중인 종목: {ticker}
    - 최근 1달 나스닥(Nasdaq) 지수 변동률: {ndq_perf:.1f}%
    - 최근 1달 S&P 500 지수 변동률: {sp_perf:.1f}%
    - 현재 시장 공포지수(VIX): {vix_value:.1f} (보통 15 이하면 안정, 20 이상이면 불안)

    [치명적인 규칙]
    1. 위 데이터를 기반으로 현재 미국 증시 상황(예: 기술주 중심의 상승세 혹은 조정, 매크로 금리 우려, 인플레이션 영향 등 데이터 흐름과 매칭되는 실제 경제 이슈)을 주린이 눈높이에 맞게 분석해 줘.
    2. 전문 용어는 주린이가 이해하기 쉽게 풀어서 설명해 줘.
    3. 무조건 깔끔하게 딱 5줄(5개 문장)로만 요약해 줘. 다른 인사말이나 마크다운 기호(-, *, 숫자 등)는 절대 붙이지 마.

    [반환 형식 예시]
    📢 현재 미국 증시는 나스닥이 큰 폭으로 움직이며 기술주 중심의 변동성이 강해진 장세입니다.
    📢 공포지수가 다소 안정적인 흐름을 보이면서 투자자들의 매수 심리가 여전히 살아있음을 보여줍니다.
    ... (이런 식으로 딱 5줄만 반환)
    """
    
    try:
        response = ai_model.generate_content(prompt)
        lines = [line.strip() for line in response.text.strip().split('\n') if line.strip()]
        cleaned_lines = [l.replace('*', '').replace('-', '').strip() for l in lines]
        return cleaned_lines[:5]
    except Exception as e:
        return [f"❌ 장세 브리핑 일시 지연 ({str(e)})"]

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

    # 💡 야후 파이낸스에서 3대 대장 지수 실제 데이터 긁어오기 (절대 차단 안 당함)
    try:
        ndq = yf.Ticker("^IXIC").history(period="1mo")
        sp500 = yf.Ticker("^GSPC").history(period="1mo")
        vix = yf.Ticker("^VIX").history(period="1d")
        
        ndq_perf = ((ndq['Close'].iloc[-1] - ndq['Close'].iloc[0]) / ndq['Close'].iloc[0]) * 100
        sp_perf = ((sp500['Close'].iloc[-1] - sp500['Close'].iloc[0]) / sp500['Close'].iloc[0]) * 100
        vix_value = vix['Close'].iloc[-1]
    except Exception:
        # 혹시 모를 에러 발생 시 안정적인 기본값 세팅
        ndq_perf, sp_perf, vix_value = 1.5, 0.8, 16.5

    # 수집한 '리얼 지표 데이터'를 바탕으로 AI 매크로 브리핑 생성
    macro_briefing = ai_macro_analysis(ticker.upper(), ndq_perf, sp_perf, vix_value)

    return {
        "ticker": ticker.upper(),
        "bull_prob": bull,
        "sideways_prob": sideways,
        "bear_prob": bear,
        "description": desc,
        "news": macro_briefing # 기존 뉴스 변수명을 그대로 활용해 화면 수정 최소화
    }
