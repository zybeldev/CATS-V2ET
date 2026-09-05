from cats.runtime.environment_doctor import inspect_environment


def main():
    # V2ET reference runtime uses local CPU embeddings and injected Qwen reasoning,
    # so an OpenAI API key is not a required environment dependency.
    checks = inspect_environment(require_openai=False)
    for check in checks:
        status = "PASS" if check.passed else "FAIL"
        print(f"{status:4}  {check.name}: {check.detail}")

    if not all(c.passed for c in checks):
        raise SystemExit(2)

    print("Environment readiness: PASS")


if __name__ == "__main__":
    main()
