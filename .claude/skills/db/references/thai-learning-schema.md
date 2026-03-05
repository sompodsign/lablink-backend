# Thai Learning DB Schema Snapshot

Generated from Django model metadata (not direct DB introspection).
Use `schema-introspection.sql` for live schema verification against Postgres.

## Table of Contents
- `django_admin_log` (admin.LogEntry)
- `ai_conversation` (ai.Conversation)
- `ai_message` (ai.Message)
- `auth_group` (auth.Group)
- `auth_permission` (auth.Permission)
- `auth_user` (auth.User)
- `blog_blogcategory` (blog.BlogCategory)
- `blog_blogpost` (blog.BlogPost)
- `blog_blogtag` (blog.BlogTag)
- `blog_comment` (blog.Comment)
- `blog_postbookmark` (blog.PostBookmark)
- `blog_postlike` (blog.PostLike)
- `blog_uploaded_file` (blog.UploadedFile)
- `django_content_type` (contenttypes.ContentType)
- `currency` (currency.Currency)
- `currency_exchange_rate` (currency.ExchangeRate)
- `django_celery_beat_clockedschedule` (django_celery_beat.ClockedSchedule)
- `django_celery_beat_crontabschedule` (django_celery_beat.CrontabSchedule)
- `django_celery_beat_intervalschedule` (django_celery_beat.IntervalSchedule)
- `django_celery_beat_periodictask` (django_celery_beat.PeriodicTask)
- `django_celery_beat_periodictasks` (django_celery_beat.PeriodicTasks)
- `django_celery_beat_solarschedule` (django_celery_beat.SolarSchedule)
- `finance_agreement` (finance.Agreement)
- `finance_budget` (finance.Budget)
- `finance_budget_item` (finance.BudgetItem)
- `finance_contact` (finance.Contact)
- `finance_earning` (finance.Earning)
- `finance_earning_category` (finance.EarningCategory)
- `finance_source` (finance.FinanceSource)
- `finance_repayment` (finance.Repayment)
- `lessons_lesson` (lessons.Lesson)
- `lessons_lessoncategory` (lessons.LessonCategory)
- `lessons_lessontemplate` (lessons.LessonTemplate)
- `django_session` (sessions.Session)
- `todos_note` (todos.Note)
- `todos_project` (todos.Project)
- `todos_subtask` (todos.SubTask)
- `todos_todo` (todos.Todo)
- `todos_tododetail` (todos.TodoDetail)
- `users_profile` (users.UserProfile)
- `api_aiexplain` (vocabulary.AIExplanation)
- `vocabulary_example` (vocabulary.Example)
- `vocabulary_exerciseset` (vocabulary.ExerciseSet)
- `vocabulary_meaning` (vocabulary.Meaning)
- `vocabulary_phrase` (vocabulary.Phrase)
- `vocabulary_phraseexercise` (vocabulary.PhraseExercise)
- `vocabulary_userword` (vocabulary.UserWord)
- `vocabulary_word` (vocabulary.Word)
- `vocabulary_wordcategory` (vocabulary.WordCategory)
- `vocabulary_wordexercise` (vocabulary.WordExercise)

## `django_admin_log`
Model: `admin.LogEntry`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `action_time` | `DateTimeField` | no | no | no | `` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `content_type_id` | `ForeignKey` | yes | no | no | `django_content_type.id` |
| `object_id` | `TextField` | yes | no | no | `` |
| `object_repr` | `CharField` | no | no | no | `` |
| `action_flag` | `PositiveSmallIntegerField` | no | no | no | `` |
| `change_message` | `TextField` | no | no | no | `` |

## `ai_conversation`
Model: `ai.Conversation`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `title` | `CharField` | no | no | no | `` |
| `language_focus` | `CharField` | no | no | no | `` |
| `is_active` | `BooleanField` | no | no | no | `` |

## `ai_message`
Model: `ai.Message`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `conversation_id` | `ForeignKey` | no | no | no | `ai_conversation.id` |
| `sender` | `CharField` | no | no | no | `` |
| `content` | `TextField` | no | no | no | `` |
| `message_type` | `CharField` | no | no | no | `` |
| `thai_text` | `TextField` | yes | no | no | `` |
| `romanization` | `TextField` | yes | no | no | `` |
| `audio_url` | `CharField` | yes | no | no | `` |
| `confidence_score` | `FloatField` | no | no | no | `` |
| `processing_time` | `FloatField` | no | no | no | `` |
| `tokens_used` | `IntegerField` | no | no | no | `` |
| `is_read` | `BooleanField` | no | no | no | `` |
| `metadata` | `JSONField` | no | no | no | `` |

## `auth_group`
Model: `auth.Group`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `name` | `CharField` | no | no | yes | `` |
| `permissions` | `ManyToManyField` | no | no | no | `auth_permission.id` |

## `auth_permission`
Model: `auth.Permission`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `name` | `CharField` | no | no | no | `` |
| `content_type_id` | `ForeignKey` | no | no | no | `django_content_type.id` |
| `codename` | `CharField` | no | no | no | `` |

## `auth_user`
Model: `auth.User`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `password` | `CharField` | no | no | no | `` |
| `last_login` | `DateTimeField` | yes | no | no | `` |
| `is_superuser` | `BooleanField` | no | no | no | `` |
| `groups` | `ManyToManyField` | no | no | no | `auth_group.id` |
| `user_permissions` | `ManyToManyField` | no | no | no | `auth_permission.id` |
| `username` | `CharField` | no | no | yes | `` |
| `first_name` | `CharField` | no | no | no | `` |
| `last_name` | `CharField` | no | no | no | `` |
| `email` | `CharField` | no | no | no | `` |
| `is_staff` | `BooleanField` | no | no | no | `` |
| `is_active` | `BooleanField` | no | no | no | `` |
| `date_joined` | `DateTimeField` | no | no | no | `` |

## `blog_blogcategory`
Model: `blog.BlogCategory`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `name` | `CharField` | no | no | yes | `` |
| `slug` | `SlugField` | no | no | yes | `` |
| `description` | `TextField` | no | no | no | `` |
| `parent_id` | `ForeignKey` | yes | no | no | `blog_blogcategory.id` |
| `order` | `PositiveIntegerField` | no | no | no | `` |

## `blog_blogpost`
Model: `blog.BlogPost`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `title` | `CharField` | no | no | no | `` |
| `slug` | `SlugField` | no | no | yes | `` |
| `content` | `TextField` | no | no | no | `` |
| `excerpt` | `TextField` | no | no | no | `` |
| `author_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `status` | `CharField` | no | no | no | `` |
| `published_at` | `DateTimeField` | yes | no | no | `` |
| `category_id` | `ForeignKey` | yes | no | no | `blog_blogcategory.id` |
| `tags` | `ManyToManyField` | no | no | no | `blog_blogtag.id` |
| `view_count` | `PositiveIntegerField` | no | no | no | `` |
| `embedding` | `VectorField` | yes | no | no | `` |
| `embedding_model` | `CharField` | no | no | no | `` |
| `embedding_updated_at` | `DateTimeField` | yes | no | no | `` |

## `blog_blogtag`
Model: `blog.BlogTag`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `name` | `CharField` | no | no | yes | `` |
| `slug` | `SlugField` | no | no | yes | `` |
| `description` | `CharField` | no | no | no | `` |

## `blog_comment`
Model: `blog.Comment`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `post_id` | `ForeignKey` | no | no | no | `blog_blogpost.id` |
| `author_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `content` | `TextField` | no | no | no | `` |
| `parent_id` | `ForeignKey` | yes | no | no | `blog_comment.id` |
| `depth` | `PositiveIntegerField` | no | no | no | `` |
| `is_deleted` | `BooleanField` | no | no | no | `` |

## `blog_postbookmark`
Model: `blog.PostBookmark`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `post_id` | `ForeignKey` | no | no | no | `blog_blogpost.id` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `notes` | `TextField` | no | no | no | `` |

## `blog_postlike`
Model: `blog.PostLike`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `post_id` | `ForeignKey` | no | no | no | `blog_blogpost.id` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |

## `blog_uploaded_file`
Model: `blog.UploadedFile`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `file_path` | `CharField` | no | no | yes | `` |
| `uploaded_by_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `uploaded_at` | `DateTimeField` | no | no | no | `` |
| `is_used` | `BooleanField` | no | no | no | `` |

## `django_content_type`
Model: `contenttypes.ContentType`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `app_label` | `CharField` | no | no | no | `` |
| `model` | `CharField` | no | no | no | `` |

## `currency`
Model: `currency.Currency`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `code` | `CharField` | no | no | yes | `` |
| `name` | `CharField` | no | no | no | `` |
| `symbol` | `CharField` | yes | no | no | `` |
| `is_active` | `BooleanField` | no | no | no | `` |

## `currency_exchange_rate`
Model: `currency.ExchangeRate`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `base_currency_code` | `ForeignKey` | no | no | no | `currency.id` |
| `target_currency_code` | `ForeignKey` | no | no | no | `currency.id` |
| `rate` | `DecimalField` | no | no | no | `` |
| `rate_date` | `DateField` | no | no | no | `` |
| `source` | `CharField` | no | no | no | `` |

## `django_celery_beat_clockedschedule`
Model: `django_celery_beat.ClockedSchedule`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `clocked_time` | `DateTimeField` | no | no | no | `` |

## `django_celery_beat_crontabschedule`
Model: `django_celery_beat.CrontabSchedule`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `minute` | `CharField` | no | no | no | `` |
| `hour` | `CharField` | no | no | no | `` |
| `day_of_month` | `CharField` | no | no | no | `` |
| `month_of_year` | `CharField` | no | no | no | `` |
| `day_of_week` | `CharField` | no | no | no | `` |
| `timezone` | `CharField` | no | no | no | `` |

## `django_celery_beat_intervalschedule`
Model: `django_celery_beat.IntervalSchedule`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `every` | `IntegerField` | no | no | no | `` |
| `period` | `CharField` | no | no | no | `` |

## `django_celery_beat_periodictask`
Model: `django_celery_beat.PeriodicTask`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `name` | `CharField` | no | no | yes | `` |
| `task` | `CharField` | no | no | no | `` |
| `interval_id` | `ForeignKey` | yes | no | no | `django_celery_beat_intervalschedule.id` |
| `crontab_id` | `ForeignKey` | yes | no | no | `django_celery_beat_crontabschedule.id` |
| `solar_id` | `ForeignKey` | yes | no | no | `django_celery_beat_solarschedule.id` |
| `clocked_id` | `ForeignKey` | yes | no | no | `django_celery_beat_clockedschedule.id` |
| `args` | `TextField` | no | no | no | `` |
| `kwargs` | `TextField` | no | no | no | `` |
| `queue` | `CharField` | yes | no | no | `` |
| `exchange` | `CharField` | yes | no | no | `` |
| `routing_key` | `CharField` | yes | no | no | `` |
| `headers` | `TextField` | no | no | no | `` |
| `priority` | `PositiveIntegerField` | yes | no | no | `` |
| `expires` | `DateTimeField` | yes | no | no | `` |
| `expire_seconds` | `PositiveIntegerField` | yes | no | no | `` |
| `one_off` | `BooleanField` | no | no | no | `` |
| `start_time` | `DateTimeField` | yes | no | no | `` |
| `enabled` | `BooleanField` | no | no | no | `` |
| `last_run_at` | `DateTimeField` | yes | no | no | `` |
| `total_run_count` | `PositiveIntegerField` | no | no | no | `` |
| `date_changed` | `DateTimeField` | no | no | no | `` |
| `description` | `TextField` | no | no | no | `` |

## `django_celery_beat_periodictasks`
Model: `django_celery_beat.PeriodicTasks`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `ident` | `SmallIntegerField` | no | yes | yes | `` |
| `last_update` | `DateTimeField` | no | no | no | `` |

## `django_celery_beat_solarschedule`
Model: `django_celery_beat.SolarSchedule`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `event` | `CharField` | no | no | no | `` |
| `latitude` | `DecimalField` | no | no | no | `` |
| `longitude` | `DecimalField` | no | no | no | `` |

## `finance_agreement`
Model: `finance.Agreement`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `owner_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `finance_type` | `CharField` | no | no | no | `` |
| `investment_category` | `CharField` | yes | no | no | `` |
| `investment_type` | `CharField` | yes | no | no | `` |
| `counterparty_id` | `ForeignKey` | yes | no | no | `finance_contact.id` |
| `direction` | `CharField` | yes | no | no | `` |
| `principal_amount` | `DecimalField` | yes | no | no | `` |
| `currency_id` | `ForeignKey` | yes | no | no | `currency.id` |
| `source_id` | `ForeignKey` | yes | no | no | `finance_source.id` |
| `agreed_date` | `DateField` | no | no | no | `` |
| `promised_repayment_date` | `DateField` | yes | no | no | `` |
| `status` | `CharField` | no | no | no | `` |
| `note` | `TextField` | yes | no | no | `` |

## `finance_budget`
Model: `finance.Budget`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `owner_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `month` | `PositiveSmallIntegerField` | no | no | no | `` |
| `year` | `PositiveIntegerField` | no | no | no | `` |
| `base_currency_id` | `ForeignKey` | yes | no | no | `currency.id` |
| `note` | `TextField` | yes | no | no | `` |
| `status` | `CharField` | no | no | no | `` |
| `metadata` | `JSONField` | no | no | no | `` |

## `finance_budget_item`
Model: `finance.BudgetItem`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `budget_id` | `ForeignKey` | no | no | no | `finance_budget.id` |
| `purpose` | `CharField` | no | no | no | `` |
| `amount` | `DecimalField` | no | no | no | `` |
| `currency_id` | `ForeignKey` | yes | no | no | `currency.id` |
| `category` | `CharField` | yes | no | no | `` |
| `is_fixed` | `BooleanField` | no | no | no | `` |
| `is_completed` | `BooleanField` | no | no | no | `` |
| `sort_index` | `PositiveIntegerField` | no | no | no | `` |
| `note` | `TextField` | yes | no | no | `` |

## `finance_contact`
Model: `finance.Contact`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `owner_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `name` | `CharField` | no | no | no | `` |
| `phone` | `CharField` | yes | no | no | `` |
| `note` | `TextField` | yes | no | no | `` |

## `finance_earning`
Model: `finance.Earning`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `budget_id` | `ForeignKey` | no | no | no | `finance_budget.id` |
| `category_id` | `ForeignKey` | yes | no | no | `finance_earning_category.id` |
| `description` | `CharField` | yes | no | no | `` |
| `amount` | `DecimalField` | no | no | no | `` |
| `currency_id` | `ForeignKey` | yes | no | no | `currency.id` |
| `sort_index` | `PositiveIntegerField` | no | no | no | `` |
| `note` | `TextField` | yes | no | no | `` |

## `finance_earning_category`
Model: `finance.EarningCategory`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `name` | `CharField` | no | no | yes | `` |
| `is_active` | `BooleanField` | no | no | no | `` |
| `sort_index` | `PositiveIntegerField` | no | no | no | `` |

## `finance_source`
Model: `finance.FinanceSource`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `name` | `CharField` | no | no | yes | `` |
| `is_active` | `BooleanField` | no | no | no | `` |

## `finance_repayment`
Model: `finance.Repayment`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `AutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `agreement_id` | `ForeignKey` | no | no | no | `finance_agreement.id` |
| `amount` | `DecimalField` | no | no | no | `` |
| `currency_id` | `ForeignKey` | yes | no | no | `currency.id` |
| `date` | `DateField` | no | no | no | `` |
| `status` | `CharField` | no | no | no | `` |
| `note` | `TextField` | yes | no | no | `` |

## `lessons_lesson`
Model: `lessons.Lesson`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `category_id` | `ForeignKey` | no | no | no | `lessons_lessoncategory.id` |
| `language` | `CharField` | no | no | no | `` |
| `title` | `CharField` | no | no | no | `` |
| `description` | `TextField` | yes | no | no | `` |
| `is_active` | `BooleanField` | no | no | no | `` |
| `ai_generated_content` | `JSONField` | yes | no | no | `` |
| `status` | `CharField` | no | no | no | `` |
| `generation_error` | `TextField` | yes | no | no | `` |

## `lessons_lessoncategory`
Model: `lessons.LessonCategory`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `name` | `CharField` | no | no | no | `` |
| `language` | `CharField` | no | no | no | `` |
| `description` | `TextField` | yes | no | no | `` |
| `order` | `IntegerField` | no | no | no | `` |
| `icon` | `CharField` | yes | no | no | `` |
| `color` | `CharField` | no | no | no | `` |

## `lessons_lessontemplate`
Model: `lessons.LessonTemplate`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `name` | `CharField` | no | no | no | `` |
| `language` | `CharField` | no | no | no | `` |
| `description` | `TextField` | no | no | no | `` |
| `lesson_type` | `CharField` | no | no | no | `` |
| `template_config` | `JSONField` | no | no | no | `` |
| `is_active` | `BooleanField` | no | no | no | `` |
| `created_by_id` | `ForeignKey` | yes | no | no | `auth_user.id` |
| `category_id` | `ForeignKey` | yes | no | no | `lessons_lessoncategory.id` |
| `usage_count` | `IntegerField` | no | no | no | `` |

## `django_session`
Model: `sessions.Session`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `session_key` | `CharField` | no | yes | yes | `` |
| `session_data` | `TextField` | no | no | no | `` |
| `expire_date` | `DateTimeField` | no | no | no | `` |

## `todos_note`
Model: `todos.Note`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `title` | `CharField` | no | no | no | `` |
| `content_json` | `JSONField` | no | no | no | `` |
| `is_pinned` | `BooleanField` | no | no | no | `` |
| `order` | `FloatField` | no | no | no | `` |

## `todos_project`
Model: `todos.Project`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `name` | `CharField` | no | no | no | `` |
| `color` | `CharField` | no | no | no | `` |
| `icon` | `CharField` | no | no | no | `` |
| `order` | `IntegerField` | no | no | no | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |

## `todos_subtask`
Model: `todos.SubTask`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `todo_id` | `ForeignKey` | no | no | no | `todos_todo.id` |
| `title` | `CharField` | no | no | no | `` |
| `is_completed` | `BooleanField` | no | no | no | `` |
| `order` | `IntegerField` | no | no | no | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |

## `todos_todo`
Model: `todos.Todo`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `project_id` | `ForeignKey` | yes | no | no | `todos_project.id` |
| `title` | `CharField` | no | no | no | `` |
| `description` | `TextField` | no | no | no | `` |
| `is_completed` | `BooleanField` | no | no | no | `` |
| `priority` | `IntegerField` | no | no | no | `` |
| `due_date` | `DateTimeField` | yes | no | no | `` |
| `recurrence_rule` | `CharField` | no | no | no | `` |
| `category` | `CharField` | no | no | no | `` |
| `recurrence_type` | `CharField` | yes | no | no | `` |
| `recurrence_interval` | `IntegerField` | no | no | no | `` |
| `recurrence_days` | `CharField` | no | no | no | `` |
| `recurrence_end_date` | `DateTimeField` | yes | no | no | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `last_completed_at` | `DateTimeField` | yes | no | no | `` |
| `order` | `FloatField` | no | no | no | `` |
| `is_notification` | `BooleanField` | no | no | no | `` |
| `notification_sent` | `BooleanField` | no | no | no | `` |
| `notification_task_id` | `CharField` | no | no | no | `` |

## `todos_tododetail`
Model: `todos.TodoDetail`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `todo_id` | `OneToOneField` | no | no | yes | `todos_todo.id` |
| `details` | `TextField` | no | no | no | `` |
| `priority` | `IntegerField` | no | no | no | `` |
| `labels` | `CharField` | no | no | no | `` |
| `time_estimate` | `IntegerField` | yes | no | no | `` |
| `time_spent` | `IntegerField` | no | no | no | `` |
| `reminder_time` | `DateTimeField` | yes | no | no | `` |
| `location` | `CharField` | no | no | no | `` |
| `url` | `CharField` | no | no | no | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |

## `users_profile`
Model: `users.UserProfile`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `user_id` | `OneToOneField` | no | no | yes | `auth_user.id` |
| `learning_language` | `CharField` | no | no | no | `` |
| `native_language` | `CharField` | no | no | no | `` |
| `gender` | `CharField` | yes | no | no | `` |
| `address` | `TextField` | yes | no | no | `` |
| `timezone` | `CharField` | no | no | no | `` |

## `api_aiexplain`
Model: `vocabulary.AIExplanation`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `content_type_id` | `ForeignKey` | yes | no | no | `django_content_type.id` |
| `object_id` | `PositiveIntegerField` | yes | no | no | `` |
| `ai_explanation` | `JSONField` | no | no | no | `` |

## `vocabulary_example`
Model: `vocabulary.Example`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `content_type_id` | `ForeignKey` | no | no | no | `django_content_type.id` |
| `object_id` | `PositiveIntegerField` | no | no | no | `` |
| `thai` | `TextField` | no | no | no | `` |
| `romanization` | `TextField` | yes | no | no | `` |
| `english` | `TextField` | no | no | no | `` |
| `bengali` | `TextField` | yes | no | no | `` |

## `vocabulary_exerciseset`
Model: `vocabulary.ExerciseSet`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `language` | `CharField` | no | no | no | `` |
| `exercise_type` | `CharField` | no | no | no | `` |
| `name` | `CharField` | no | no | no | `` |
| `description` | `TextField` | yes | no | no | `` |
| `is_active` | `BooleanField` | no | no | no | `` |

## `vocabulary_meaning`
Model: `vocabulary.Meaning`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `word_id` | `OneToOneField` | no | no | yes | `vocabulary_word.id` |
| `language` | `CharField` | no | no | no | `` |
| `meaning` | `TextField` | no | no | no | `` |
| `definition` | `TextField` | yes | no | no | `` |
| `context` | `CharField` | yes | no | no | `` |
| `romanization` | `CharField` | yes | no | no | `` |
| `thai_audio_url` | `CharField` | yes | no | no | `` |
| `bengali` | `CharField` | yes | no | no | `` |
| `part_of_speech` | `CharField` | yes | no | no | `` |
| `notes` | `TextField` | yes | no | no | `` |
| `synonyms` | `ArrayField` | no | no | no | `` |

## `vocabulary_phrase`
Model: `vocabulary.Phrase`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `text` | `TextField` | no | no | no | `` |
| `translation` | `TextField` | yes | no | no | `` |
| `source_lang` | `CharField` | no | no | no | `` |
| `target_lang` | `CharField` | no | no | no | `` |
| `learning_platform` | `CharField` | no | no | no | `` |
| `is_favorite` | `BooleanField` | no | no | no | `` |
| `context` | `CharField` | yes | no | no | `` |
| `pronunciation_guide` | `CharField` | yes | no | no | `` |
| `notes` | `TextField` | yes | no | no | `` |

## `vocabulary_phraseexercise`
Model: `vocabulary.PhraseExercise`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `exercise_set_id` | `ForeignKey` | no | no | no | `vocabulary_exerciseset.id` |
| `phrase_id` | `ForeignKey` | no | no | no | `vocabulary_phrase.id` |
| `is_active` | `BooleanField` | no | no | no | `` |
| `practice_count` | `IntegerField` | no | no | no | `` |
| `consecutive_correct` | `IntegerField` | no | no | no | `` |
| `total_correct` | `IntegerField` | no | no | no | `` |
| `total_attempts` | `IntegerField` | no | no | no | `` |
| `is_mastered` | `BooleanField` | no | no | no | `` |
| `mastered_at` | `DateTimeField` | yes | no | no | `` |
| `last_practiced_at` | `DateTimeField` | yes | no | no | `` |
| `next_review_at` | `DateTimeField` | yes | no | no | `` |
| `ease_factor` | `FloatField` | no | no | no | `` |
| `interval_days` | `IntegerField` | no | no | no | `` |

## `vocabulary_userword`
Model: `vocabulary.UserWord`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `user_id` | `ForeignKey` | no | no | no | `auth_user.id` |
| `word_id` | `ForeignKey` | no | no | no | `vocabulary_word.id` |
| `is_favorite` | `BooleanField` | no | no | no | `` |

## `vocabulary_word`
Model: `vocabulary.Word`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `text` | `CharField` | no | no | no | `` |
| `language` | `CharField` | no | no | no | `` |
| `learning_platform` | `CharField` | no | no | no | `` |
| `synonyms` | `ArrayField` | no | no | no | `` |
| `romanizations` | `ArrayField` | yes | no | no | `` |
| `ipa_list` | `ArrayField` | yes | no | no | `` |
| `easy_text` | `CharField` | yes | no | no | `` |
| `users` | `ManyToManyField` | no | no | no | `auth_user.id` |
| `categories` | `ManyToManyField` | no | no | no | `vocabulary_wordcategory.id` |

## `vocabulary_wordcategory`
Model: `vocabulary.WordCategory`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `name` | `CharField` | no | no | no | `` |
| `slug` | `SlugField` | no | no | no | `` |
| `parent_id` | `ForeignKey` | yes | no | no | `vocabulary_wordcategory.id` |
| `type` | `CharField` | no | no | no | `` |
| `description` | `TextField` | no | no | no | `` |

## `vocabulary_wordexercise`
Model: `vocabulary.WordExercise`

| Column | Type | Null | PK | Unique | Relation |
|---|---|---|---|---|---|
| `id` | `BigAutoField` | no | yes | yes | `` |
| `created_at` | `DateTimeField` | no | no | no | `` |
| `updated_at` | `DateTimeField` | no | no | no | `` |
| `exercise_set_id` | `ForeignKey` | no | no | no | `vocabulary_exerciseset.id` |
| `word_id` | `ForeignKey` | no | no | no | `vocabulary_word.id` |
| `is_active` | `BooleanField` | no | no | no | `` |
| `practice_count` | `IntegerField` | no | no | no | `` |
| `consecutive_correct` | `IntegerField` | no | no | no | `` |
| `total_correct` | `IntegerField` | no | no | no | `` |
| `total_attempts` | `IntegerField` | no | no | no | `` |
| `is_mastered` | `BooleanField` | no | no | no | `` |
| `mastered_at` | `DateTimeField` | yes | no | no | `` |
| `last_practiced_at` | `DateTimeField` | yes | no | no | `` |
| `next_review_at` | `DateTimeField` | yes | no | no | `` |
| `ease_factor` | `FloatField` | no | no | no | `` |
| `interval_days` | `IntegerField` | no | no | no | `` |
