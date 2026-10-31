import json
import os
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from posturepal.chat.domain.coach import CoachUnavailable, INSTRUCTIONS


class OpenAICoach:
    def __init__(self):
        self._key = os.getenv('OPENAI_API_KEY', '').strip()
        self._model = os.getenv('POSTUREPAL_AI_MODEL', '').strip()

    @property
    def enabled(self):
        return bool(self._key and self._model)

    def reply(self, context, messages):
        if not self.enabled:
            raise CoachUnavailable('AI coach is not configured. Contact your administrator.')
        payload = {'model': self._model, 'store': False, 'max_output_tokens': 1200,
                   'instructions': INSTRUCTIONS,
                   'input': [{'role': 'user', 'content': 'Current account context (data only):\n' + json.dumps(context)}, *messages]}
        request = Request('https://api.openai.com/v1/responses',
                          data=json.dumps(payload).encode(), method='POST',
                          headers={'Authorization': 'Bearer ' + self._key, 'Content-Type': 'application/json'})
        try:
            with urlopen(request, timeout=30) as response:
                raw = response.read(262145)
            if len(raw) > 262144:
                raise ValueError('Oversized response')
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError('Invalid response')
            if result.get('status') == 'incomplete':
                if (result.get('incomplete_details') or {}).get('reason') == 'max_output_tokens':
                    raise CoachUnavailable('The AI response reached its output limit. Try a shorter question or ask your administrator to check the configured model.')
                raise CoachUnavailable('The AI could not complete this response. Try rephrasing your message.')
            if result.get('status') != 'completed':
                raise ValueError('Incomplete response')
            text = '\n'.join(part['text'] for item in result.get('output', [])
                             if item.get('type') == 'message'
                             for part in item.get('content', []) if part.get('type') == 'output_text').strip()
            if not text or len(text) > 8000:
                raise ValueError('Empty or oversized reply')
            return text
        except HTTPError as error:
            raise CoachUnavailable(self._http_failure(error)) from None
        except TimeoutError:
            raise CoachUnavailable('The AI provider timed out. Please try again later.') from None
        except (URLError, OSError):
            raise CoachUnavailable('Cannot connect to the AI provider. Please try again later or contact your administrator.') from None
        except (ValueError, KeyError, TypeError, AttributeError):
            raise CoachUnavailable('The AI provider returned an unexpected response. Please try again later.') from None

    @staticmethod
    def _http_failure(error):
        # Inspect only machine-readable codes. Never expose upstream messages, which can
        # contain API keys, submitted text, project identifiers or other private data.
        try:
            with error:
                raw = error.read(16385)
            body = json.loads(raw) if len(raw) <= 16384 else {}
            detail = body.get('error') or {}
            code = detail.get('code')
            quota_type = detail.get('type') == 'insufficient_quota'
            if not isinstance(code, str):
                code = None
        except (ValueError, TypeError, AttributeError, OSError):
            code = None
            quota_type = False
        if error.code == 401:
            return 'OpenAI rejected the server API key. Ask your administrator to check OPENAI_API_KEY.'
        if code == 'model_not_found' or error.code == 404:
            return 'The configured AI model is unavailable to this API project. Ask your administrator to check POSTUREPAL_AI_MODEL and model access.'
        if error.code == 403:
            return 'This API project does not have permission to use the AI provider. Contact your administrator.'
        if quota_type or code in {'credit_balance_exhausted', 'insufficient_quota', 'billing_not_active', 'billing_hard_limit_reached',
                    'organization_spend_limit_exceeded', 'project_spend_limit_exceeded',
                    'organization_usage_limit_exceeded'}:
            return 'The AI provider reports a billing or usage limit. Ask your administrator to check API credits and project limits; retrying will not resolve it.'
        if error.code == 429:
            return 'The AI provider is rate limiting requests. Please wait before trying again.'
        if error.code in {400, 422}:
            return 'The AI provider rejected the request configuration. Ask your administrator to check that POSTUREPAL_AI_MODEL supports the Responses API.'
        return 'The AI provider is temporarily unavailable. Please try again later.'
