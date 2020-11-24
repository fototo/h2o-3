setwd(normalizePath(dirname(R.utils::commandArgs(asValues=TRUE)$"f")))
source("../../../scripts/h2o-r-test-setup.R")
library(mgcv)


# simple test to make sure we can invoke early stop in R for GAM.  Heavy testing is done in Python.  We
# are just testing the client API.
test.model.gam.thin.plates <- function() {
    data(trees)
    ct1 <- gam(Volume ~ s(Height, Girth, k = 25), family=Gamma(link=log), data=trees)
}

doTest("GAM with thin plate regression splines with cherry", test.model.gam.thin.plates)
