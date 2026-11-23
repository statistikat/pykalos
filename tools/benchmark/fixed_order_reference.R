# Replay the original fixed-order reference generator and its pinned public JVM frontends.
args <- commandArgs(trailingOnly = TRUE)
stopifnot(length(args) == 5L)
core <- normalizePath(args[1])
tooling <- file.path(core, "validation/reference")
source(file.path(tooling, "common.R"))
source(file.path(tooling, "extended-fixtures.R"))
source(file.path(tooling, "arma-fit-reference.R"))
generator <- file.path(core, "validation/fixtures/native/arma-fit-cases.R")
source(generator)
warmup <- as.integer(args[3]); samples <- as.integer(args[4]); batch <- as.integer(args[5])
flags <- c("-XX:ActiveProcessorCount=1", "-Djava.util.concurrent.ForkJoinPool.common.parallelism=1")
options(java.parameters = flags)
pin <- extended_assert_oracle(reference_fixture_dir(core))
all_cases <- arma_fit_cases()
cases <- Filter(function(case) case$period == 12L && case$kind %in% c("airline", "mixed_factors"), all_cases)
stopifnot(length(cases) == 8L)
scalar <- jsonlite::unbox
# Exact binary64 text, including the original observations and fixed coefficients.
decimal <- function(x) sprintf("%.17g", as.numeric(x))
encode <- function(case) {
  a <- case$arguments
  values <- as.numeric(a$series); missing <- is.na(values); values[missing] <- 0
  list(values = decimal(values), missing = missing, rows = range(case$rows),
       from = a$estimation_start, to = a$estimation_end, d = scalar(case$d), D = scalar(case$D),
       start = start(a$series), regressors = lapply(a$regressors, decimal),
       transformation = scalar(a$transformation), blocks = lapply(case$specification, function(x) {
         fixed <- !is.na(x); x[!fixed] <- 0; list(initial = decimal(x), fixed = fixed)
       }))
}
summarize <- function(result) {
  blocks <- lapply(c("phi", "theta", "bphi", "btheta"), function(key) {
    values <- result$description$arima[[key]]
    if (is.null(values)) return(numeric())
    sign <- if (key %in% c("phi", "bphi")) -1 else 1
    decimal(sign * as.numeric(values["value", ]))
  })
  names(blocks) <- c("ar", "ma", "seasonal_ar", "seasonal_ma")
  lk <- result$estimation$likelihood
  list(coefficients = blocks, adjustedll = scalar(decimal(lk$adjustedll)),
       jacobian = scalar(decimal(lk$adjustedll - lk$ll)))
}
measure <- function(method) {
  execute <- reference_executor(method)
  prepared <- lapply(cases, prepare_reference, method = method)
  expected <- lapply(prepared, function(item) summarize(execute(item)))
  for (round in seq_len(warmup)) for (item in prepared) execute(item)
  timings <- lapply(prepared, function(x) numeric())
  for (round in seq_len(samples)) for (id in names(prepared)) {
    item <- prepared[[id]]
    started <- proc.time()[["elapsed"]]
    for (i in seq_len(batch)) last <- execute(item)
    elapsed <- proc.time()[["elapsed"]] - started
    stopifnot(identical(summarize(last), expected[[id]]))
    timings[[id]] <- c(timings[[id]], 1000 * elapsed / batch)
  }
  list(expected = expected, ms = timings)
}
jsonlite::write_json(list(inputs = lapply(cases, encode), x13 = measure("x13"),
  tramo = measure("tramoseats"), runtime = list(java = lapply(pin$java, scalar),
  r = scalar(R.version.string), packages = lapply(pin$packages, function(p) scalar(p$Version)),
  jvm_flags = flags, generator_sha256 = scalar(reference_sha256(generator)),
  manifest_sha256 = scalar(reference_sha256(file.path(reference_fixture_dir(core), "oracle-manifest.R"))))),
  args[2], digits = NA)
