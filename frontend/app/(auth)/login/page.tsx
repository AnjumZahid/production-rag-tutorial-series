"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ArrowRight, Eye, EyeOff, LockKeyhole, Sparkles } from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { ApiError } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const { login, isAuthenticated, loading } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && isAuthenticated) router.replace("/chat");
  }, [isAuthenticated, loading, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError("");

    try {
      await login(email.trim(), password);
      router.replace("/chat");
    } catch (err) {
      const message =
        err instanceof ApiError
          ? err.message
          : "Unable to sign in. Please try again.";

      setError(message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-shell">
      <div className="auth-visual" aria-hidden="true">
        <div className="auth-visual-orb auth-orb-one" />
        <div className="auth-visual-orb auth-orb-two" />

        <div className="auth-visual-content">
          <div className="brand-mark large">
            <Sparkles size={25} strokeWidth={1.8} />
          </div>

          <p className="eyebrow">Private knowledge workspace</p>

          <h1>
            Ask your documents.
            <br />
            Keep the evidence close.
          </h1>

          <p>
            Upload PDFs, retrieve grounded answers, and trace every response
            back to its source.
          </p>
        </div>
      </div>

      <div className="auth-panel">
        <div className="auth-card">
          <div className="auth-mobile-brand">
            <div className="brand-mark">
              <Sparkles size={20} />
            </div>

            <strong>Knowledge Chat</strong>
          </div>

          <div className="auth-heading">
            <span className="auth-icon">
              <LockKeyhole size={20} />
            </span>

            <h2>Welcome back</h2>

            <p>Sign in to continue to your secure workspace.</p>
          </div>

          <form onSubmit={handleSubmit} className="form-stack">
            <label className="field-label">
              Email address
              <input
                className="text-input"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                placeholder="you@example.com"
                required
              />
            </label>

            <label className="field-label">
              Password
              <span className="password-field">
                <input
                  className="text-input"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="Enter your password"
                  required
                />

                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword((value) => !value)}
                  aria-label={showPassword ? "Hide password" : "Show password"}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              </span>
            </label>

            {error ? (
              <div className="form-error" role="alert">
                {error}
              </div>
            ) : null}

            <button
              className="primary-button wide"
              type="submit"
              disabled={submitting || loading}
            >
              {submitting ? (
                <span className="spinner small" />
              ) : (
                <>
                  Sign in <ArrowRight size={17} />
                </>
              )}
            </button>
          </form>

          <p className="auth-switch">
            New to Knowledge Chat? <Link href="/register">Create an account</Link>
          </p>

          <p className="auth-footnote">
            Tokens are kept in this browser tab and cleared when you sign out.
          </p>

          <p className="auth-credit">
            Designed and developed by <strong>Anjum Zahid</strong>
          </p>
        </div>
      </div>
    </section>
  );
}