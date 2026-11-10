import { ref, type Ref } from 'vue'

import { useToast } from '@/composables/useToast'
import { searchSourcesApi } from '@/api/sources'

// HDHive OAuth 授权流程：发起授权页 → 粘贴回调 URL → 换取 Token 并回填到渠道字段值
export function useHdhiveOauth(sourceValues: Ref<Record<string, Record<string, any>>>) {
  const { toast } = useToast()
  const sourceOauthBusy = ref<'' | 'start' | 'exchange'>('')
  const sourceOauthCallback = ref('')

  function hdhivePayload() {
    const values = sourceValues.value.hdhive || {}
    return {
      client_id: String(values.hdhive_client_id || '').trim(),
      redirect_uri: String(values.hdhive_redirect_uri || '').trim(),
      response_mode: String(values.hdhive_response_mode || 'redirect'),
      scope: 'query unlock write',
    }
  }

  async function startHdhiveOauth() {
    sourceOauthBusy.value = 'start'
    try {
      const payload = hdhivePayload()
      const result = await searchSourcesApi.hdhiveOauthStart(payload)
      sourceOauthCallback.value = ''
      window.open(result.authorize_url, '_blank', 'noopener')
      toast('已打开授权页，完成后把回调 URL 粘贴回来', 'success')
    } catch (cause) {
      toast(cause instanceof Error ? cause.message : '发起授权失败', 'error')
    } finally {
      sourceOauthBusy.value = ''
    }
  }

  async function exchangeHdhiveOauth() {
    sourceOauthBusy.value = 'exchange'
    try {
      const payload = hdhivePayload()
      const values = sourceValues.value.hdhive || {}
      const result = await searchSourcesApi.hdhiveOauthExchange({
        ...payload,
        app_secret: String(values.hdhive_api_key || '').trim(),
        callback: sourceOauthCallback.value.trim(),
      })
      values.hdhive_access_token = result.access_token
      values.hdhive_refresh_token = result.refresh_token
      sourceValues.value.hdhive = { ...values }
      sourceOauthCallback.value = ''
      toast(result.warning || 'HDHive 授权成功，Token 已填入，保存后生效', result.warning ? 'error' : 'success')
    } catch (cause) {
      toast(cause instanceof Error ? cause.message : '授权校验失败', 'error')
    } finally {
      sourceOauthBusy.value = ''
    }
  }

  return { sourceOauthBusy, sourceOauthCallback, startHdhiveOauth, exchangeHdhiveOauth }
}
