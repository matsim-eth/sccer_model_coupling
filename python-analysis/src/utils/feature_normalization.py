import pandas as pd

def normalize_features( data_frame ):
    feature_names = data_frame.columns.values
    norm_features = pd.DataFrame( {'agentId' : data_frame[ 'agentId' ] } )

    for i in range(1,len( feature_names ) ):
        feature = feature_names[ i ]
        mean = data_frame[ feature ].sum() / len( data_frame[ feature ])
        std = sum( abs( data_frame[ feature ] - mean ) )
        norm_features[ feature ] = (data_frame[ feature ] - mean) / std

    return norm_features
