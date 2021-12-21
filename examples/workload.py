import time

from pyspark import SparkContext
from pyspark.sql import SparkSession, SQLContext
from pyspark.sql import functions as f

dataset_labels = ["small", "medium", "large"]
dataset_sizes = [1000000, 100000000, 1000000000]
dataset_repartitions = [1, 10, 10]
num_tries = 15

def runExperiment(ds1, ds2, strat):
    if strat == "merge":
        sqlContext.setConf("spark.sql.planner.sortMergeJoin", "true")
        sqlContext.setConf("spark.sql.autoBroadcastJoinThreshold", 0)
    elif strat == "hash":
        sqlContext.setConf("spark.sql.planner.sortMergeJoin", "false")
        sqlContext.setConf("spark.sql.autoBroadcastJoinThreshold", 0)
    elif strat == "broadcast":
        sqlContext.setConf("spark.sql.broadcastTimeout", 36000)
        sqlContext.setConf("spark.sql.autoBroadcastJoinThreshold", 5000000000)
        print(f"@@@strategy: {strat}; {dataset_labels[ds1]}-{dataset_labels[ds2]}; time taken:")
    for i in range(num_tries):
        df1 = ''
        df2 = ''
        df1 = sqlContext.range(0, dataset_sizes[ds1]) \
                        .repartition(dataset_repartitions[ds1])
        df2 = sqlContext.range(0, dataset_sizes[ds2]) \
                        .repartition(dataset_repartitions[ds2])
        startingTime = time.time()
        joinedDF = df1 \
            .alias("a") \
            .join(df2.alias("b"), f.col("a.id") == f.col("b.id"))
        joinedDF.count()
        endingTime = time.time()
        print(f'@@@{endingTime - startingTime}')
        
if __name__ == "__main__":
    spark = SparkSession\
        .builder\
        .appName("workload generator")\
        .getOrCreate()
    sc = spark.sparkContext
    sqlContext = SQLContext(sc)
    print("Warming up")
    for i in range(20):
        df = ''
        df = sqlContext.range(0, 1000000).repartition(10)
        startingTime = time.time()
        joinedDF = df \
            .alias("a") \
            .join(df.alias("b"), f.col("a.id") == f.col("b.id"))
        joinedDF.count()
        endingTime = time.time()

    runExperiment(0, 0, "merge")
    runExperiment(0, 1, "merge")
    runExperiment(0, 2, "merge")
    runExperiment(1, 1, "merge")
    runExperiment(1, 2, "merge")
    runExperiment(2, 2, "merge")
    runExperiment(0, 0, "hash")
    runExperiment(0, 1, "hash")
    runExperiment(0, 2, "hash")
    runExperiment(1, 1, "hash")
    runExperiment(1, 2, "hash")
    runExperiment(2, 2, "hash")
    runExperiment(0, 0, "broadcast")
    runExperiment(0, 1, "broadcast")
    runExperiment(0, 2, "broadcast")
    runExperiment(1, 1, "broadcast")
    runExperiment(1, 2, "broadcast")
    runExperiment(2, 2, "broadcast")
