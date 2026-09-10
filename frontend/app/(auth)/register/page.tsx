"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import {
  ArrowRight,
  Building2,
  Eye,
  EyeOff,
  Sparkles,
  UserPlus,
} from "lucide-react";
import { useAuth } from "@/components/providers/auth-provider";
import { ApiError } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const { register, isAuthenticated, loading } = useAuth();
  const [fullName, setFullName] = useState("");
  const [organizationName, setOrganizationName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && isAuthenticated) router.replace("/chat");
  }, [isAuthenticated, loading, router]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (password.length < 12) {
      setError("Password must contain at least 12 characters.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setSubmitting(true);

    try {
      await register({
        full_name: fullName.trim(),
        organization_name: organizationName.trim(),
        email: email.trim(),
        password,
      });

      router.replace("/chat");
    } catch (err) {
      setError(
        err instanceof ApiError
          ? err.message
          : "Unable to create your account.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="auth-shell">
      <div className="auth-visual register-visual" aria-hidden="true">
        <div className="auth-visual-orb auth-orb-one" />
        <div className="auth-visual-orb auth-orb-two" />

        <div className="auth-visual-content">
          <div className="brand-mark large">
            <Sparkles size={25} strokeWidth={1.8} />
          </div>

          <p className="eyebrow">Built for focused teams</p>

          <h1>
            Your documents.
            <br />
            Your answers. Your control.
          </h1>

          <p>
            Each organization gets isolated users, documents, retrieval, and
            role-based access.
          </p>
        </div>
      </div>

      <div className="auth-panel register-panel">
        <div className="auth-card register-card">
          <div className="auth-mobile-brand">
            <div className="brand-mark">
              <Sparkles size={20} />
            </div>

            <strong>Knowledge Chat</strong>
          </div>

          <div className="auth-heading">
            <span className="auth-icon">
              <UserPlus size={20} />
            </span>

            <h2>Create your workspace</h2>

            <p>The first account becomes the organization owner.</p>
          </div>

          <form onSubmit={handleSubmit} className="form-stack">
            <div className="form-grid-two">
              <label className="field-label">
                Full name
                <input
                  className="text-input"
                  value={fullName}
                  onChange={(event) => setFullName(event.target.value)}
                  placeholder="Your name"
                  required
                  minLength={2}
                  maxLength={120}
                />
              </label>

              <label className="field-label">
                Organization
                <span className="input-with-icon">
                  <Building2 size={17} />

                  <input
                    className="text-input"
                    value={organizationName}
                    onChange={(event) =>
                      setOrganizationName(event.target.value)
                    }
                    placeholder="Research Lab"
                    required
                    minLength={2}
                    maxLength={120}
                  />
                </span>
              </label>
            </div>

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
                  autoComplete="new-password"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="At least 12 characters"
                  required
                  minLength={12}
                  maxLength={128}
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

            <label className="field-label">
              Confirm password
              <input
                className="text-input"
                type="password"
                autoComplete="new-password"
                value={confirmPassword}
                onChange={(event) => setConfirmPassword(event.target.value)}
                placeholder="Repeat your password"
                required
                minLength={12}
                maxLength={128}
              />
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
                  Create workspace <ArrowRight size={17} />
                </>
              )}
            </button>
          </form>

          <p className="auth-switch">
            Already have an account? <Link href="/login">Sign in</Link>
          </p>

          <p className="auth-credit">
            Designed and developed by <strong>Anjum Zahid</strong>
          </p>
        </div>
      </div>
    </section>
  );
}