-- everyone orders in their own first month
select cohort_month, retention
from {{ ref('cohorts') }}
where months_since_first = 0 and retention <> 1
