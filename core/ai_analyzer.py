import json
import os
from typing import Any

import dashscope
from dashscope import Generation
from log import logger


class AIAnalyzer:
    def __init__(self, api_key: str | None = None, model: str = "qwen-turbo"):
        dashscope.api_key = api_key or os.getenv("DASHSCOPE_API_KEY", "")
        self.model = model

    def analyze_news(
        self, symbol: str, news_text: str
    ) -> dict[str, Any]:
        prompt = f"""你是一名严谨的金融分析助手。请分析以下新闻对{symbol}价格的潜在影响。

严格要求：
1. 只根据新闻原文内容做判断，不得编造新闻中未提及的数字、事件或预测
2. 如果新闻信息不足以判断影响方向，sentiment_score输出0，并在reasoning中说明"信息不足"
3. impact_level的判断要基于新闻类型（如：重大监管政策 > 交易所公告 > 一般市场消息）

输出JSON格式（不要输出其他内容）：
{{
  "sentiment_score": -1到1之间的浮点数,
  "impact_level": "高/中/低",
  "reasoning": "简要理由，需引用新闻原文中的具体依据",
  "confidence": 0到1之间，表示你对这个判断的把握程度
}}

新闻内容：{news_text}
"""
        try:
            response = Generation.call(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                result_format="message",
            )
            content = response.output.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"analyze_news failed: {e}")
            return {
                "sentiment_score": 0.0,
                "impact_level": "低",
                "reasoning": f"分析失败: {e}",
                "confidence": 0.0,
            }

    def generate_factor(
        self, symbol: str, metrics: dict[str, Any]
    ) -> dict[str, Any]:
        prompt = f"""基于以下{symbol}的市场数据，识别异常信号并生成因子假设。

数据：{json.dumps(metrics, ensure_ascii=False, indent=2)}

要求：
1. 只做定性解读，不做数值计算
2. 标注异常来源（具体哪个指标、什么数值）
3. 低置信度的信号明确标注

输出JSON：
{{
  "factors": [
    {{
      "name": "因子名称",
      "signal": "bullish/bearish/neutral",
      "confidence": 0到1,
      "reasoning": "依据说明",
      "source_metric": "来源指标"
    }}
  ]
}}
"""
        try:
            response = Generation.call(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                result_format="message",
            )
            content = response.output.choices[0].message.content
            return json.loads(content)
        except Exception as e:
            logger.error(f"generate_factor failed: {e}")
            return {"factors": []}
