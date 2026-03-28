import { useEffect, useEffectEvent } from 'react'

function shouldIgnoreHotkey(target) {
  if (!(target instanceof HTMLElement)) {
    return false
  }

  const tag = target.tagName.toLowerCase()
  if (target.isContentEditable) {
    return true
  }

  return tag === 'input' || tag === 'textarea' || tag === 'select'
}

export function useGameHotkeys(bindings, enabled = true) {
  const onKeyDown = useEffectEvent((event) => {
    if (!enabled || shouldIgnoreHotkey(event.target)) {
      return
    }

    const key = event.key.toLowerCase()
    const withMeta = event.ctrlKey || event.metaKey

    if (withMeta && key === 's') {
      event.preventDefault()
      bindings.onSave?.()
      return
    }

    if (withMeta && key === 'z') {
      event.preventDefault()
      bindings.onUndo?.()
      return
    }

    if (withMeta && key === 'y') {
      event.preventDefault()
      bindings.onRedo?.()
      return
    }

    if (withMeta) {
      return
    }

    const actionMap = {
      n: bindings.onNewAtBat,
      r: bindings.onRunnerEvent,
      s: bindings.onSubstitution,
      g: bindings.onEndGame,
      l: bindings.onToggleLog,
      t: bindings.onSwitchTab,
      q: bindings.onQuit,
    }

    const handler = actionMap[key]
    if (handler) {
      event.preventDefault()
      handler()
    }
  })

  useEffect(() => {
    if (!enabled) {
      return undefined
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [enabled, onKeyDown])
}

