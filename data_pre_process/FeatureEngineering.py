from pyspark.ml.clustering import KMeans
import matplotlib.pyplot as plt
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, count, row_number, rank, size, split, when, expr, lit, dense_rank,trim,udf,length
from pyspark.sql.window import Window
from pyspark.ml.feature import Tokenizer, HashingTF, IDF
from pyspark.ml.linalg import Vectors
from pyspark.ml import Pipeline
from pyspark.ml.feature import StringIndexer, VectorAssembler
from rapidfuzz.fuzz import ratio
from pyspark.sql.types import DoubleType

# 1. Similarity between company about and job listing about
def compute_about_similarity(full_data):


    # Define a function to calculate similarity
    def calculate_similarity(about, company_description_gemini):
        if about is None or company_description_gemini is None:
            return 0.0  # Handle missing values
        return float(ratio(about, company_description_gemini))

    # Register the UDF
    calculate_similarity_udf = udf(calculate_similarity, DoubleType())

    # Apply the function to create a new column for given spark df 
    udf_calculate_similarity = udf(calculate_similarity, DoubleType())
    full_data = full_data.withColumn(
        "about_similarity", 
        calculate_similarity_udf("about", "company_description_gemini")
    )
    return full_data

# 3. Has company logo
def add_company_logo_feature(companies_df):
    return companies_df.withColumn("has_logo", when(col("logo")== 'https://static.licdn.com/aero-v1/sc/h/cs8pjfgyw96g44ln9r7tct85f', lit(0)).otherwise(lit(1)))

# 4. Affiliate length in ratio to max length in table
def compute_affiliate_length_ratio(companies_df):
    companies_df = companies_df.withColumn("affiliate_len", size(col("affiliated")))
    max_affiliate_len = companies_df.agg({"affiliate_len": "max"}).collect()[0][0]
    return companies_df.withColumn("affiliate_ratio", col("affiliate_len") / lit(max_affiliate_len))

# 5. Compare columns to industry average
def compare_to_industry_avg(companies_df):
    industry_avg = companies_df.groupBy("industries").agg(
        avg("followers").alias("avg_followers"),
        avg("employees_in_linkedin").alias("avg_employees")
    )
    companies_df = companies_df.join(industry_avg, "industries", how="left")
    companies_df = companies_df.withColumn(
        "followers_to_avg", (col("followers") - col("avg_followers")) / col("avg_followers")
    )
    companies_df = companies_df.withColumn("employees_to_avg", (col("employees_in_linkedin") - col("avg_employees")) / col("avg_employees"))
    return companies_df

# 6. Rank companies within industries
def rank_companies_within_industries(companies_df):
    window_spec = Window.partitionBy("industries").orderBy(col("followers").desc())
    companies_df = companies_df.withColumn("industry_rank", dense_rank().over(window_spec))
    industry_count = companies_df.groupBy("industries").agg(count("id").alias("industry_total"))
    companies_df = companies_df.join(industry_count, "industries", how="left")
    return companies_df.withColumn("industry_rank_score", 1-(col("industry_rank") / col("industry_total")))

def add_company_clusters(companies_df, num_clusters):
    # Extract country code from headquarters after the comma
    companies_df = companies_df.withColumn(
        "country",
        when(
            col("headquarters").contains(", "),
            trim(split(col("headquarters"), ", ").getItem(1))
        ).otherwise("Unknown")
    )
    # Add length features with null handling
    companies_df = companies_df.withColumn("investors_len", when(col("investors").isNotNull(), size("investors")).otherwise(0))
    companies_df = companies_df.withColumn("updates_len", when(col("updates").isNotNull(), size("updates")).otherwise(0))
    companies_df = companies_df.withColumn("funding_rounds", col("funding.rounds").cast("double"))

    # Fill missing values for numeric columns
    companies_df = companies_df.fillna({
        "followers": 0,
        "employees_in_linkedin": 0,
        "founded": 0,
        "funding_rounds":0
    })

    # Index categorical columns with null handling
    indexers = [
        StringIndexer(inputCol="company_size", outputCol="company_size_index").setHandleInvalid("keep"),
        StringIndexer(inputCol="organization_type", outputCol="organization_type_index").setHandleInvalid("keep"),
        StringIndexer(inputCol="industries", outputCol="industries_index").setHandleInvalid("keep"),
        StringIndexer(inputCol="country", outputCol="country_index").setHandleInvalid("keep")
    ]

    # Assemble all features
    feature_columns = [
        "followers", "employees_in_linkedin", "founded","funding_rounds",
        "company_size_index", "organization_type_index", "industries_index",
        "country_index", "investors_len", "updates_len"
    ]
    assembler = VectorAssembler(inputCols=feature_columns, outputCol="features")

    # Clustering model
    kmeans = KMeans(k=num_clusters, seed=42).setFeaturesCol("features")

    # Pipeline
    pipeline = Pipeline(stages=indexers + [assembler, kmeans])

    # Fit the pipeline and transform the data
    model = pipeline.fit(companies_df)
    clustered_df = model.transform(companies_df).withColumnRenamed("prediction", "cluster_number")

    return clustered_df

# 8. Diversity in employee subtitles
from pyspark.sql.functions import col, expr, size, lit, explode

def compute_employee_subtitle_diversity(companies_df):
    # Explode the employees array to get individual employee entries
    exploded_df = companies_df.withColumn("employee", explode("employees"))
    
    # Extract the 'subtitle' field from the exploded structs
    exploded_df = exploded_df.withColumn("employee_subtitle", col("employee.subtitle"))
    
    # Aggregate back to get unique subtitles per company
    diversity_df = exploded_df.groupBy("company_id").agg(
        expr("size(array_distinct(collect_list(employee_subtitle)))").alias("unique_subtitles")
    )
    
    # Calculate the maximum diversity
    max_diversity = diversity_df.agg({"unique_subtitles": "max"}).collect()[0][0]
    
    # Join the unique_subtitles back to the original DataFrame
    companies_with_diversity = companies_df.join(diversity_df, on="company_id", how="left")
    
    # Compute subtitle diversity ratio
    return companies_with_diversity.withColumn(
        "subtitle_diversity_ratio", col("unique_subtitles") / lit(max_diversity)
    )

# 9. Compare funding to companies in the same industry or size
def compare_funding(companies_df):
    industry_size_avg = companies_df.groupBy("industries", "company_size").agg(
        avg("funding_rounds").alias("avg_funding_rounds")
    )
    companies_df = companies_df.join(industry_size_avg, ["industries", "company_size"], how="left")
    return companies_df.withColumn(
        "funding_to_avg", (col("funding_rounds") - col("avg_funding_rounds")) / col("avg_funding_rounds")
    )

def companies_df_feature_engineering(companies_df):
    companies_df = add_company_logo_feature(companies_df)
    companies_df = compute_affiliate_length_ratio(companies_df)
    companies_df = compare_to_industry_avg(companies_df)
    companies_df = rank_companies_within_industries(companies_df)
    companies_df = add_company_clusters(companies_df, num_clusters=30)
    companies_df = compute_employee_subtitle_diversity(companies_df)
    companies_df = compare_funding(companies_df)
    return companies_df

def full_data_transformation(full_data_df):
    full_data_df = compute_about_similarity(full_data_df)
    full_data_df = full_data_df.withColumn("description_len", length("job_description"))
    return full_data_df