export function FullScreenSpinner() {
  return (
    <div
      role="status"
      aria-label="로딩 중"
      className="fixed inset-0 flex items-center justify-center bg-background/80 backdrop-blur-sm z-50"
    >
      <div className="flex flex-col items-center gap-4">
        <div
          className="h-10 w-10 animate-spin rounded-full border-4 border-primary border-t-transparent"
          aria-hidden="true"
        />
        <p className="text-sm text-muted-foreground">로딩 중...</p>
      </div>
    </div>
  )
}
