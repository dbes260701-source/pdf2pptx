# 기여자

## 사람

- **[@dbes260701-source](https://github.com/dbes260701-source)** — 프로젝트 소유자.
  파이프라인 설계와 초기 구현(추출·빌드·표 인식·렌더링 검수), 배포용 exe 패키징,
  제3자 라이선스 정리, 사내 문서군에 대한 overrides 작성.

## AI 도구

이 저장소의 일부는 [Claude Code](https://claude.com/claude-code)로 작성되었다.
아래는 git 이력에 `Co-authored-by` 트레일러로 기록된 것만 적은 것이며,
트레일러가 없는 커밋은 포함하지 않는다.

- **Claude (Anthropic)** — `Co-authored-by: Claude Opus 5 <noreply@anthropic.com>`

  | 커밋 | 내용 |
  |---|---|
  | [`1e18759`](https://github.com/dbes260701-source/pdf2pptx/commit/1e18759) | 외부 평가 두 건의 P0 항목 반영 — `quality.py` 품질 게이트와 종료 코드 규약, 회귀 테스트 29건(음성 대조군 포함), `.gitignore` 신설과 빌드/작업 산출물 추적 해제, `pyproject.toml`·`requirements*.txt`·`LICENSE`, `docs/EVALUATION-RESPONSE.md`·`docs/ROADMAP.md`, CI 워크플로 |

  이 작업 중 발견해 수정한 결함: 렌더러 부재 시 파생 증상("슬라이드 0장")이
  근본 원인("렌더러 없음")을 가리던 종료 코드 우선순위 문제.

### 왜 GitHub Contributors 목록에는 안 보이는가

GitHub의 Contributors 그래프는 **커밋 이메일이 실제 GitHub 계정에 연결되어 있을 때만**
집계된다. `Co-authored-by` 트레일러도 같은 규칙을 따르므로,
GitHub 계정이 없는 `noreply@anthropic.com` 은 커밋 페이지에 공동 작성자로 표시될 뿐
사이드바 Contributors 에는 나타나지 않는다. 이 파일이 그 자리를 대신한다.

> 참고: [Creating a commit with multiple authors](https://docs.github.com/en/pull-requests/committing-changes-to-your-project/creating-and-editing-commits/creating-a-commit-with-multiple-authors) ·
> [Viewing a project's contributors](https://docs.github.com/en/repositories/viewing-activity-and-data-for-your-repository/viewing-a-projects-contributors)

## 표기 원칙

- AI 도구가 관여한 커밋에는 `Co-authored-by` 트레일러를 단다. 사후에 소급 추가하지 않는다.
- 이 파일에는 git 이력으로 확인되는 것만 적는다.
- 최종 책임은 변경을 검토하고 병합한 사람에게 있다.
