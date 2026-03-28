export function Modal({ title, children, onClose, wide = false }) {
  return (
    <div className="modal-scrim" role="presentation" onClick={onClose}>
      <div
        className={`modal-shell ${wide ? 'modal-shell-wide' : ''}`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="modal-head">
          <h2>{title}</h2>
          <button className="ghost-button" type="button" onClick={onClose} aria-label="Close">
            Close
          </button>
        </div>
        {children}
      </div>
    </div>
  )
}

