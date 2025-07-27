# Requirements Document

## Introduction

Cursor 문서 사이트(https://docs.cursor.com/)의 모든 콘텐츠를 크롤링하여 단일 PDF 파일로 변환하는 Python 기반 시스템입니다. 이 시스템은 NotebookLM의 출처로 사용될 고품질 PDF를 생성하며, 불필요한 UI 요소를 제거하고 콘텐츠만 추출하여 가독성을 최적화합니다.

## Requirements

### Requirement 1

**User Story:** 개발자로서, Cursor 문서 사이트의 모든 페이지를 자동으로 크롤링하고 싶습니다. 그래야 수동으로 각 페이지를 방문하지 않고도 전체 문서를 수집할 수 있습니다.

#### Acceptance Criteria

1. WHEN 시스템이 시작되면 THEN 시스템은 https://docs.cursor.com/ 을 시작점으로 설정해야 합니다
2. WHEN 페이지를 크롤링할 때 THEN 시스템은 해당 페이지의 모든 하위 링크를 발견해야 합니다
3. WHEN 링크를 발견할 때 THEN 시스템은 docs.cursor.com 도메인 내의 링크만 수집해야 합니다
4. WHEN 중복된 URL을 발견할 때 THEN 시스템은 해당 URL을 한 번만 처리해야 합니다
5. WHEN 해시태그 링크(#)를 발견할 때 THEN 시스템은 해당 링크를 무시해야 합니다

### Requirement 2

**User Story:** 사용자로서, 크롤링된 콘텐츠에서 불필요한 UI 요소가 제거되기를 원합니다. 그래야 PDF에서 실제 문서 내용만 읽을 수 있습니다.

#### Acceptance Criteria

1. WHEN 페이지를 파싱할 때 THEN 시스템은 사이드바 요소를 제거해야 합니다
2. WHEN 페이지를 파싱할 때 THEN 시스템은 헤더 네비게이션을 제거해야 합니다
3. WHEN 페이지를 파싱할 때 THEN 시스템은 푸터 요소를 제거해야 합니다
4. WHEN 페이지를 파싱할 때 THEN 시스템은 광고나 프로모션 배너를 제거해야 합니다
5. WHEN 메인 콘텐츠를 추출할 때 THEN 시스템은 제목, 본문, 이미지만 포함해야 합니다

### Requirement 3

**User Story:** 사용자로서, 이미지가 포함된 PDF를 원하지만 YouTube 비디오는 링크로 대체되기를 원합니다. 그래야 PDF 크기를 관리하면서도 시각적 정보를 유지할 수 있습니다.

#### Acceptance Criteria

1. WHEN 이미지를 발견할 때 THEN 시스템은 이미지를 다운로드하고 PDF에 포함해야 합니다
2. WHEN YouTube 비디오를 발견할 때 THEN 시스템은 비디오를 링크 텍스트로 대체해야 합니다
3. WHEN 이미지 다운로드가 실패할 때 THEN 시스템은 대체 텍스트나 링크를 표시해야 합니다
4. WHEN 이미지가 너무 클 때 THEN 시스템은 적절한 크기로 조정해야 합니다

### Requirement 4

**User Story:** 사용자로서, PDF의 페이지들이 논리적인 순서로 정렬되기를 원합니다. 그래야 문서를 순차적으로 읽을 수 있습니다.

#### Acceptance Criteria

1. WHEN PDF를 생성할 때 THEN 시스템은 URL 경로를 기준으로 페이지를 정렬해야 합니다
2. WHEN 같은 레벨의 페이지들이 있을 때 THEN 시스템은 알파벳 순으로 정렬해야 합니다
3. WHEN 하위 페이지들이 있을 때 THEN 시스템은 상위 페이지 다음에 배치해야 합니다
4. WHEN 인덱스나 홈페이지가 있을 때 THEN 시스템은 해당 페이지를 맨 앞에 배치해야 합니다

### Requirement 5

**User Story:** 개발자로서, 크롤링 과정을 모니터링하고 오류를 추적할 수 있기를 원합니다. 그래야 문제가 발생했을 때 디버깅할 수 있습니다.

#### Acceptance Criteria

1. WHEN 크롤링이 시작될 때 THEN 시스템은 진행 상황을 로그로 출력해야 합니다
2. WHEN 페이지 크롤링이 실패할 때 THEN 시스템은 오류를 로그에 기록하고 계속 진행해야 합니다
3. WHEN 크롤링이 완료될 때 THEN 시스템은 수집된 페이지 수와 소요 시간을 보고해야 합니다
4. WHEN 중복 URL이 발견될 때 THEN 시스템은 해당 정보를 로그에 기록해야 합니다

### Requirement 6

**User Story:** 사용자로서, 고품질의 PDF 파일을 얻고 싶습니다. 그래야 NotebookLM에서 텍스트를 정확하게 인식할 수 있습니다.

#### Acceptance Criteria

1. WHEN PDF를 생성할 때 THEN 시스템은 텍스트를 검색 가능한 형태로 저장해야 합니다
2. WHEN PDF를 생성할 때 THEN 시스템은 적절한 폰트와 크기를 사용해야 합니다
3. WHEN 코드 블록을 처리할 때 THEN 시스템은 고정폭 폰트를 사용해야 합니다
4. WHEN 제목을 처리할 때 THEN 시스템은 계층 구조를 유지해야 합니다
5. WHEN 링크를 처리할 때 THEN 시스템은 클릭 가능한 링크로 유지해야 합니다