// Configure-time provider probe used by cmake/FindKalosOpenBLAS.cmake.
// The build must fail at configure time unless the resolved headers compile
// and the resolved library links the LAPACKE entry point whose absence made
// the first baseline wheel fail at Python import.
#include <lapacke.h>

static int kalos_probe_lapacke_dpotrf_work(void) {
  lapack_int n = 1;
  lapack_int lda = 1;
  double a[1] = {1.0};
  return (int)LAPACKE_dpotrf_work(LAPACK_ROW_MAJOR, 'L', n, a, lda);
}

int main(void) { return kalos_probe_lapacke_dpotrf_work(); }
