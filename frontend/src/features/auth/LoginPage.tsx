import { LoginForm } from './LoginForm'

export function LoginPage() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-background">
      <div className="w-full max-w-md space-y-6 p-8">
        <div className="text-center">
          <h1 className="text-2xl font-bold tracking-tight">관리자 로그인</h1>
          <p className="text-sm text-muted-foreground mt-2">
            SCM v2 관리 시스템
          </p>
        </div>
        <div className="bg-card border rounded-lg p-6 shadow-sm">
          <LoginForm />
        </div>
      </div>
    </div>
  )
}
